from collections.abc import Sequence
import datetime
import json
import requests
from openapi_core import create_spec
from openapi_core.schema.parameters.enums import ParameterLocation
import yaml

import tapy.errors

def _seq_but_not_str(obj):
    """
    Determine if an object is a Sequence, i.e., has an iteratable type, but not a string, bytearray, etc.
    :param obj: Any python object.
    :return:
    """
    return isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray))


RESOURCES = ['actors',
             'meta',
             #'files', ## currently the files spec is missing operationId's for some of its operations.
             'sk',
             'tenants',
             'tokens',]

def _getspec(resource_name):
    """
    Returns the openapi spec
    :param resource_name: (str) the name of the resource.
    :return: (openapi_core.schema.specs.models.Spec) The Spec object associated with this resource.
    """
    try:
        # for now, hardcode the paths; we could look these up based on a canonical URL once that is
        # established.
        spec_path = f'/home/tapis/tapy/dyna/resources/openapi_v3-{resource_name}.yml'
        spec_dict = yaml.load(open(spec_path, 'r'))
        return create_spec(spec_dict)
    except Exception as e:
        print(f"Got exception trying to load spec_path: {spec_path}; exception: {e}")
        raise e


RESOURCE_SPECS = {resource: _getspec(resource) for resource in RESOURCES}

class DynaTapy(object):
    """
    A dynamic client for the Tapis API.
    """

    def __init__(self,
                 base_url=None,
                 username=None,
                 tenant_id=None,
                 account_type=None,
                 access_token=None,
                 refresh_token=None,
                 jwt=None,
                 x_tenant_id=None,
                 x_username=None,
                 verify=True
                 ):
        # the base_url for the server this Tapis client should interact with
        self.base_url = base_url

        # the username associated with this Tapis client
        self.username = username

        # the tenant id associated with this Tapis client
        self.tenant_id = tenant_id

        # the account_type ("user" or "service") associated with this Tapis client
        self.account_type = account_type

        # the access token to use -- should be an honest TapisResult access token.
        self.access_token = access_token

        # the refresh token to use -- should be an honest TapisResult refresh token.
        self.refresh_token = refresh_token

        # pass in a "raw" JWT directly. This is only used if the access_token is not set.
        self.jwt = jwt

        # use the following two parameters to set headers to make requests on behalf of a different
        # tenant_id and username.
        self.x_tenant_id = x_tenant_id
        self.x_username = x_username
        # it the caller did not explicitly set the x_tenant_id and x_username headers, and this is a service token
        # set them for the caller.
        if not self.x_tenant_id and not self.x_username:
            if self.account_type == 'service':
                self.x_tenant_id = self.tenant_id
                self.x_username = self.username

        # whether to verify the TLS certificate at the base_url
        self.verify = verify

        # the requests.Session object this client will use to prepare requests
        self.requests_session = requests.Session()

        # create resources for each API defined above. In the future we could make this more dynamic in multiple ways.
        for resource_name, spec in RESOURCE_SPECS.items():
            # each API is a top-level attribute on the DynaTapy object, a Resource object constructed as follows:
            setattr(self, resource_name, Resource(resource_name, spec.paths, self))

    def get_tokens(self, **kwargs):
        """
        Calls the Tapis Tokens API to get access and refresh tokens and set them on the client.
        :return: 
        """
        if not 'username' in kwargs:
            username = self.username
        if not 'tenant_id' in kwargs:
            tenant_id = self.tenant_id
        if not 'access_token_ttl' in kwargs:
            # default to a 24 hour access token -
            access_token_ttl = 86400
        if not 'refresh_token_ttl' in kwargs:
            # default to 1 year refresh token -
            refresh_token_ttl = 3153600000
        tokens = self.tokens.create_token(token_username=username,
                                          token_tenant_id=tenant_id,
                                          account_type=self.account_type,
                                          access_token_ttl=access_token_ttl,
                                          generate_refresh_token=True,
                                          refresh_token_ttl=refresh_token_ttl)
        self.set_access_token(tokens.access_token)
        self.set_refresh_token(tokens.refresh_token)

    def set_access_token(self, token):
        """
        Set the access token to be used in this session.
        :param token: (TapisResult) A TapisResult object returned using the t.tokens.create_token() method.
        :return:
        """

        def _expires_in():
            return self.access_token.expires_at - datetime.datetime.now(datetime.timezone.utc)

        self.access_token = token
        # avoid circular imports by nesting this import here - the common.auth module has to import dynatapy at
        # initialization to make create service clients.
        try:
            from common.auth import validate_token
            self.access_token.claims = validate_token(self.access_token.access_token)
            self.access_token.original_ttl = self.access_token.expires_in
            self.access_token.expires_in = _expires_in
            self.access_token.expires_at = datetime.datetime.fromtimestamp(self.access_token.claims['exp'], datetime.timezone.utc)
        except:
            pass


    def set_refresh_token(self, token):
        """
        Set the refresh token to be used in this session.
        :param token: (TapisResult) A TapisResult object returned using the t.tokens.create_token() method.
        :return:
        """
        self.refresh_token = token

    def set_jwt(self, jwt):
        """
        Set a
        :param jwt: (str) Set the JWT to be used in this session.
        :return:
        """
        self.jwt = jwt

    def get_access_jwt(self):
        """
        Returns the JWT string to use for requests.
        :return:
        """
        if hasattr(self, 'access_token') and hasattr(self.access_token, 'access_token'):
            return self.access_token.access_token
        if hasattr(self, 'jwt'):
            return self.jwt
        return None

    def set_tenant(self, tenant_id, base_url):
        """
        Reconfigure the client to interact with a specific tenant; particularly useful for services that need to serve
        multiple tenants.
        :param tenant_id: (str) The tenant_id to configure the client to interact with.
        :param base_url: (str) The base_url of the tenant to configure the client to interact with.
        :return:
        """
        self.tenant_id = tenant_id
        self.base_url = base_url


class Resource(object):
    """
    Represents a top-level API "resource" defined by an OpenAPI spec file. 
    """

    def __init__(self, resource_name, resource_spec, tapis_client):
        """
        Instantiate a resource. 
        :param resource_name: (str) The name of the resource, such as "files", "apps", etc. 
        :param resource_spec: (openapi_core.schema.specs.models.Spec) The Spec object associated with this resource. 
        :param tapis_client: (tapy.Tapis) Pointer to the Tapis object to which this resource will be attached. 
        """
        # resource_name is something like "files", "apps", etc.
        self.resource_name = resource_name

        # resource_spec is the associated definition from the spec file.
        self.resource_spec = resource_spec

        # tapis_client stores configuration data (api_server, token, etc..)
        self.tapis_client = tapis_client

        # Here we create an attr on the object for each operation_id in the spec. The attr is itself an
        # Operation object, defined below, with a special __call__ method.
        # Examples operation_id's inclue "list_files", "upload_file", etc...
        for path_name, path_desc in self.resource_spec.items():
            # Each path_desc is an openapi_core.schema.paths.models.Path object
            # it has an operations object, which is a dictionary of operations associated with the path:
            for op, op_desc in path_desc.operations.items():
                # each op_desc is an openapi_core.schema.operations.models.Operation object.
                # the op_desc has a number of associated attributes, including operation_id, parameters, path_name, etc.
                # we create an Operation object for each one of these:
                if not op_desc.operation_id:
                    print(f"invalid op_dec for {resource_name}; missing operation_id. op_dec: {op_desc}")
                    continue
                setattr(self, op_desc.operation_id, Operation(self.resource_name, op_desc, self.tapis_client))


class Operation(object):
    """
    Represents a single operation on an API resource defined by an OpenAPI spec file.
    Operation objects are in one-to-one correspondence with operation_id's defined in the spec file.     
    """

    def __init__(self, resource_name, op_desc, tapis_client):
        """
        Instantiate an operation. The op_desc should an openapi_core Operation object associated with the operation. 
        :param resource_name: (str) The resource associated with this operation.
        :param op_desc: (openapi_core.schema.operations.models.Operation) OpenAPI description of the operation. 
        :param tapis_client: Pointer to the Tapis object to which this resource will be attached.
        :return: 
        """
        self.resource_name = resource_name
        self.op_desc = op_desc
        self.tapis_client = tapis_client

        # derived attributes - for convenience
        self.operation_id = op_desc.operation_id
        self.http_method = op_desc.http_method
        self.path_parameters = [p for _, p in op_desc.parameters.items() if p.location == ParameterLocation.PATH]
        self.query_parameters = [p for _, p in op_desc.parameters.items() if p.location == ParameterLocation.QUERY]
        self.request_body = op_desc.request_body

    def __call__(self, **kwargs):
        """
        Turns the operation object into a callable. Arguments must be passed as kwargs, where the name of each kwarg 
        corresponds to a "parameter" in the OpenApi definition. Here, parameter could be a path parameter, body
        parameter, or query parameter. 
         
        :param kwargs: All allowable arguments to this operation.
         
        :return: 
        """
        # the http method is defined by the operation -
        http_method = self.http_method.upper()

        # construct the http path -
        # some API definitions, such as SK, chose to not include the "/v3/" at the beginning of their paths, so we add it in:
        if not self.op_desc.path_name.startswith('/v3/'):
            self.url = f'{self.tapis_client.base_url}/v3{self.op_desc.path_name}' # base url
        else:
            self.url = f'{self.tapis_client.base_url}{self.op_desc.path_name}'  # base url
        url = self.url
        for param in self.path_parameters:
            # look for the name in the kwargs
            if param.required:
                if param.name not in kwargs:
                    raise tapy.errors.InvalidInputError(msg=f"{param.name} is a required argument.")
            p_val = kwargs.pop(param.name)
            if param.required and not p_val:
                raise tapy.errors.InvalidInputError(msg=f"{param.name} is a required argument and cannot be None.")
            # replace the parameter in the path template with the parameter value
            s = '{' + f'{param.name}' + '}'
            url = url.replace(s, p_val)

        # construct the http query parameters -
        params = {}
        for param in self.query_parameters:
            # look for the name in the kwargs
            if param.required:
                if param.name not in kwargs:
                    raise tapy.errors.InvalidInputError(msg=f"{param.name} is a required argument.")
            # only set the parameter if it was actually sent in the function -
            if param.name in kwargs:
                p_val = kwargs.pop(param.name, None)
                params[param.name] = p_val

        # construct the http headers -
        headers = {}

        # set the X-Tapis-Token header using the client
        if self.tapis_client.get_access_jwt():
            headers = {'X-Tapis-Token': self.tapis_client.get_access_jwt(), }

        # the X-Tapis-Tenant and X-Tapis-Username headers can be set when the token represents a service account and the
        # service is making a request on behalf of another user/tenant.
        if self.tapis_client.x_tenant_id:
            headers['X-Tapis-Tenant'] = self.tapis_client.x_tenant_id
        if self.tapis_client.x_username:
            headers['X-Tapis-User'] = self.tapis_client.x_username

        # allow arbitrary headers to be passed in via the special "headers" kwarg -
        try:
            headers.update(kwargs.pop('headers', {}))
        except ValueError:
            raise tapy.errors.InvalidInputError(msg="The headers argument, if passed, must be a dictionary-like object.")

        # construct the data -
        data = None
        # these are the list of allowable request bofy content types; ex., 'application/json'.
        if hasattr(self.op_desc.request_body, 'content') and hasattr(self.op_desc.request_body.content, 'keys'):
            if 'application/json' in self.op_desc.request_body.content.keys() \
                    or '*/*' in self.op_desc.request_body.content.keys():
                headers['Content-Type'] = 'application/json'
                required_fields = self.op_desc.request_body.content['application/json'].schema.required
                data = {}
                for p_name, p_desc in self.op_desc.request_body.content['application/json'].schema.properties.items():
                    if p_name in kwargs:
                        data[p_name] = kwargs[p_name]
                    elif p_name in required_fields:
                        raise tapy.errors.InvalidInputError(msg=f'{p_name} is a required argument.')
                # serialize data before passing it to the request
                data = json.dumps(data)
        # todo - handle other body content types..

        # create a prepared request -
        # cf., https://requests.kennethreitz.org/en/master/user/advanced/#request-and-response-objects
        r = requests.Request(http_method,
                             url,
                             params=params,
                             data=data,
                             headers=headers).prepare()

        # make the request and return the response object -
        try:
            resp = self.tapis_client.requests_session.send(r, verify=self.tapis_client.verify)
        except Exception as e:
            # todo - handle different types of requests exceptions
            msg = f"Unable to make request to Tapis server. Exception: {e}"
            raise tapy.errors.BaseTapyException(msg=msg, request=r)
        # try to get the error message and version from the Tapis request:
        try:
            error_msg = resp.json().get('message')
        except:
            error_msg = resp.content
        try:
            version = resp.json().get('version')
        except:
            version = None
        # for any kind of non-20x response, we need to raise an error.
        if resp.status_code in (400, 404):
            raise tapy.errors.InvalidInputError(msg=error_msg, version=version, request=r, response=resp)
        if resp.status_code in (401, 403):
            raise tapy.errors.NotAuthorizedError(msg=error_msg, version=version, request=r, response=resp)
        if resp.status_code in (500, ):
            raise tapy.errors.ServerDownError(msg=error_msg, version=version, request=r, response=resp)
        # catch-all for any other non-20x response:
        if resp.status_code >= 300:
            raise tapy.errors.BaseTapyException(msg=error_msg, version=version, request=r, response=resp)

        # get the result's operation ids from the custom x-response-operation-ids for this operation id.from
        # results_operation_ids = [...]
        # resp.headers is a case-insensitive dict, but the v
        resp_content_type = resp.headers.get('content-type')
        if hasattr(resp_content_type, 'lower') and resp_content_type.lower() == 'application/json':
            try:
                json_content = resp.json()
            except Exception as e:
                msg = f'Requests could not produce JSON from the response even though the content-type was ' \
                      f'application/json. Exception: {e}'
                #raise tapy.errors.InvalidServerResponseError(msg=error_msg, version=version, request=r, response=resp)
                return resp.content
            # get the Tapis result objectm which could be a JSON object or list.
            try:
                result = json_content.get('result')
            except Exception as e:
                msg =  f'Request did not produce json response'
                return resp.content
                # handle responses that do not have the standard Tapis stanzas.
            if result:
                # if it is a list we should return a list of TapisResult objects:
                if _seq_but_not_str(result):
                    if len([item for item in result if type(item) in TapisResult.PRIMITIVE_TYPES]) > 0:
                        return TapisResult(result)
                    else:
                        return [TapisResult(**x) for x in result]
                # otherwise, assume it is a JSON object and return that directly as a result -
                try:
                    return TapisResult(**result)
                except Exception as e:
                    msg = f'Failed to serialize the result object. Got exception: {e}'
                    raise tapy.errors.InvalidServerResponseError(msg=msg, version=version, request=r, response=resp)
            else:
                # the response was JSON but not the standard Tapis 4 stanzas, so just return the JSON content:
                return json_content

        # todo - note:
        # For now, we do not try to handle other content-types, such as application/xml, etc. We just return
        # the raw content as the result.
        return resp.content


class TapisResult(object):
    """
    Represents a result returned from a single Tapis operation.
    """

    PRIMITIVE_TYPES = [int, str, bool, bytearray, bytes, float, type(None)]
    def __init__(self, *args, **kwargs):
        if args and kwargs:
            msg = f"Could not instantiate result object; constructor got args and kwargs. args={args}; kwargs={kwargs}"
            raise tapy.errors.BaseTapyException(msg=msg)
        # is passing non-key-value args, there should be only one arg;
        # it should be either a list or a primitive type:
        if args:
            if len(args) > 1:
                msg = f"Could not instantiate result object; constructor got args of length > 1. args={args}."
                raise tapy.errors.BaseTapyException(msg=msg)
            arg = args[0]
            # the arg is a list and not a string, there are two cases: 1) at least one object in the list is a
            # primitive type, in which case we just return a list of the objects
            if _seq_but_not_str(arg):
                setattr(self, 'result', [x for x in arg])
            else:
                setattr(self, 'result', arg)

        for k, v in kwargs.items():
            # primitive types
            if type(v) in TapisResult.PRIMITIVE_TYPES:
                # just set the attribute to the value
                setattr(self, k, v)
            # lists
            elif _seq_but_not_str(v):
                # if the list has even one item of primitive type, just return a list
                if len([item for item in v if type(item) in TapisResult.PRIMITIVE_TYPES]) > 0:
                    setattr(self, k, v)
                else:
                    setattr(self, k, [TapisResult(**item) for item in v])
            # for complex objects, create a TapisResult with the value
            else:
                setattr(self, k, TapisResult(**v))

    def __str__(self):
        attrs = '\n'.join([f'{str(a)}: {getattr(self, a)}' for a in dir(self) if not a.startswith('__') and not a.startswith('PRIMITIVE_TYPES')])
        return f'\n{attrs}'

    def __repr__(self):
        return str(self)

