from base64 import b64encode
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


RESOURCES = [('actors', 'https://raw.githubusercontent.com/TACC/abaco/master/docs/specs/openapi_v3.yml'),
             ('authenticator', 'https://raw.githubusercontent.com/tapis-project/authenticator/dev/service/resources/openapi_v3.yml'),
             ('meta','https://raw.githubusercontent.com/tapis-project/tapis-client-java/master/meta-client/src/main/resources/metav3-openapi.yaml'),
             ('files', 'https://raw.githubusercontent.com/tapis-project/tapis-files/master/api/src/main/resources/openapi.yaml'),  ## currently the files spec is missing operationId's for some of its operations.
             ('sk', 'https://raw.githubusercontent.com/tapis-project/tapis-client-java/master/security-client/src/main/resources/SKAuthorizationAPI.yaml'),
             ('streams', 'https://raw.githubusercontent.com/tapis-project/streams-api/dev/service/resources/openapi_v3.yml'),
             ('systems', 'https://raw.githubusercontent.com/tapis-project/tapis-client-java/master/systems-client/SystemsAPI.yaml'),
             ('tenants', 'https://raw.githubusercontent.com/tapis-project/tenants-api/master/service/resources/openapi_v3.yml'),
             ('tokens','https://raw.githubusercontent.com/tapis-project/tokens-api/master/service/resources/openapi_v3.yml'),]

def _getspec(resource_name, resource_url, download_spec=False):
    """
    Returns the openapi spec
    :param resource_name: (str) the name of the resource.
    :param resource_url: (str) URL to download the resource spec file.
    :return: (openapi_core.schema.specs.models.Spec) The Spec object associated with this resource.
    """
    if download_spec:
        try:
            response = requests.get(resource_url)
            if response.status_code == 200:
               try:
                   spec_dict = yaml.load(response.content)
                   return create_spec(spec_dict)
        # for now, if there are errors trying to fetch the latest spec, we fall back to the spec files defined in the
        # the python-sdk package;
               except:
                   pass
        except:
            pass

    try:
        # for now, hardcode the paths; we could look these up based on a canonical URL once that is
        # established.
        spec_path = f'/home/tapis/tapy/dyna/resources/openapi_v3-{resource_name}.yml'
        spec_dict = yaml.load(open(spec_path, 'r'))
        return create_spec(spec_dict)
    except Exception as e:
        print(f"Got exception trying to load spec_path: {spec_path}; exception: {e}")
        raise e

RESOURCE_SPECS = {resource[0]: _getspec(resource[0], resource[1]) for resource in RESOURCES}


def get_basic_auth_header(username, password):
    """
    Convenience function with will return a properly formatted Authorization header from a username and password.
    """
    user_pass = bytes(f"{username}:{password}", 'utf-8')
    return 'Basic {}'.format(b64encode(user_pass).decode())


class DynaTapy(object):
    """
    A dynamic client for the Tapis API.
    """

    def __init__(self,
                 base_url=None,
                 username=None,
                 password=None,
                 tenant_id=None,
                 account_type=None,
                 access_token=None,
                 refresh_token=None,
                 jwt=None,
                 x_tenant_id=None,
                 x_username=None,
                 verify=True,
                 service_password=None,
                 client_id=None,
                 client_key=None,
                 download_latest_specs=False
                 ):
        # the base_url for the server this Tapis client should interact with
        self.base_url = base_url

        # the username associated with this Tapis client
        self.username = username

        # the password associated with a user account; use service_password for service accounts.
        self.password = password

        # the tenant id associated with this Tapis client
        self.tenant_id = tenant_id

        # the account_type ("user" or "service") associated with this Tapis client
        self.account_type = account_type
        if not self.account_type:
            self.account_type = 'user'

        # the access token to use -- should be an honest TapisResult access token.
        self.access_token = access_token

        # the refresh token to use -- should be an honest TapisResult refresh token.
        self.refresh_token = refresh_token

        # pass in a "raw" JWT directly. This is only used if the access_token is not set.
        self.jwt = jwt

        # whether to verify the TLS certificate at the base_url
        self.verify = verify

        # the service password, for service accounts to retrieve a token with.
        self.service_password = service_password

        # the client id of an OAuth2 client to use for generating tokens
        self.client_id = client_id

        # the client key of an OAuth2 client to use for generating tokens
        self.client_key = client_key

        # the requests.Session object this client will use to prepare requests
        self.requests_session = requests.Session()

        # use the following two parameters to set headers to make requests on behalf of a different
        # tenant_id and username.
        self.x_tenant_id = x_tenant_id
        self.x_username = x_username

        # whether to dowload the very latest OpenAPI v3 definition files for the services -- setting this to True
        # could result in "live updates" to your code without warning. It also adds significant overhead to this method.
        # Use at your own risk!
        self.download_latest_specs = download_latest_specs

        if self.download_latest_specs:
            resource_specs = {resource[0]: _getspec(resource[0], resource[1], download_spec=True)
                              for resource in RESOURCES}
        else:
            resource_specs= RESOURCE_SPECS

        # create resources for each API defined above. In the future we could make this more dynamic in multiple ways.
        for resource_name, spec in resource_specs.items():
            # each API is a top-level attribute on the DynaTapy object, a Resource object constructed as follows:
            setattr(self, resource_name, Resource(resource_name, spec.paths, self))

        # if the user passed just base_url, try to get the list of tenants and derive the tenant_id from it.
        if base_url and not tenant_id:
                tenants = self.tenants.list_tenants()
                for t in tenants:
                    if t.base_url == base_url:
                        self.tenant_id = t.tenant_id

        # it the caller did not explicitly set the x_tenant_id and x_username headers, and this is a service token
        # set them for the caller.
        if not self.x_tenant_id and not self.x_username:
            if self.account_type == 'service':
                self.x_tenant_id = self.tenant_id
                self.x_username = self.username

    def get_tokens(self, **kwargs):
        """
        Convenience wrapper to get either service tokens (tokengen Tokens API) or user tokens (Authenticator/OAuth2 API)
        based on the account_type on this client instance.
        """
        if self.account_type == 'service':
            return self.get_service_tokens(**kwargs)
        return self.get_user_tokens(**kwargs)


    def get_user_tokens(self, **kwargs):
        """
        Calls the Tapis authenticator to get user tokens based on username and password.
        """
        if not 'username' in kwargs:
            username = self.username
        else:
            username = kwargs['username']
        if not 'password' in kwargs:
            password = self.password
        else:
            password = kwargs['password']
        if not 'client_id' in kwargs:
            client_id = self.client_id
        else:
            client_id = kwargs['client_id']
        if not 'client_key' in kwargs:
            client_key = self.client_key
        else:
            client_key = kwargs['client_key']
        if client_id and client_key:
            auth_header = {'Authorization': get_basic_auth_header(client_id, client_key)}
        else:
            auth_header = {}
        if 'headers' in kwargs:
            auth_header.update(kwargs['headers'])
        tokens = self.authenticator.create_token(username=username,
                                                 password=password,
                                                 grant_type='password',
                                                 headers=auth_header)
        self.set_access_token(tokens.access_token)
        self.refresh_token = None
        #
        if hasattr(tokens, 'refresh_token'):
            self.set_refresh_token(tokens.refresh_token)


    def get_service_tokens(self, **kwargs):
        """
        Calls the Tapis Tokens API (tokengen) to get access and refresh tokens for a service and set them on the client.
        :return: 
        """
        if not 'username' in kwargs:
            username = self.username
        else:
            username = kwargs['username']
        if not 'tenant_id' in kwargs:
            tenant_id = self.tenant_id
        else:
            tenant_id = kwargs['tenant_id']
        if not 'access_token_ttl' in kwargs:
            # default to a 24 hour access token -
            access_token_ttl = 86400
        else:
            access_token_ttl = kwargs['access_token_ttl']
        if not 'refresh_token_ttl' in kwargs:
            # default to 1 year refresh token -
            refresh_token_ttl = 3153600000
        else:
            refresh_token_ttl = kwargs['refresh_token_ttl']
        service_password = None
        if 'service_password' in kwargs:
            service_password = kwargs['service_password']
        elif self.service_password:
            service_password = self.service_password

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

    def refresh_tokens(self):
        """
        Use the refresh token on this client to get a new access and refresh token pair.
        """
        if not self.refresh_token:
            raise tapy.errors.TapyClientConfigurationError(msg="No refresh token found.")
        if self.account_type == 'service':
            return self.refresh_service_tokens()
        else:
            return self.refresh_user_tokens()

    def refresh_user_tokens(self):
        """
        Use the refresh token operation for tokens of type "user".
        """
        if not self.client_id:
            raise tapy.errors.TapyClientConfigurationError(msg="client_id not configure.")
        if not self.client_key:
            raise tapy.errors.TapyClientConfigurationError(msg="client_key not configure.")
        auth_header = {'Authorization': get_basic_auth_header(self.client_id, self.client_key)}
        tokens = self.authenticator.create_token(grant_type='refresh_token',
                                                 refresh_token=self.refresh_token.refresh_token,
                                                 headers=auth_header)
        self.set_access_token(tokens.access_token)
        self.set_refresh_token(tokens.refresh_token)

    def refresh_service_tokens(self):
        """
        Use the refresh token operation for tokens of type "service".
        """
        tokens = self.tokens.refresh_token(refresh_token=self.refresh_token.refresh_token)
        self.set_access_token(tokens.access_token)
        self.set_refresh_token(tokens.refresh_token)

    def set_refresh_token(self, token):
        """
        Set the refresh token to be used in this session.
        :param token: (TapisResult) A TapisResult object returned using the t.tokens.create_token() method.
        :return:
        """
        def _expires_in():
            return self.refresh_token.expires_at - datetime.datetime.now(datetime.timezone.utc)

        self.refresh_token = token
        # avoid circular imports by nesting this import here - the common.auth module has to import dynatapy at
        # initialization to make create service clients.
        try:
            from common.auth import validate_token
            self.refresh_token.claims = validate_token(self.refresh_token.refresh_token)
            self.refresh_token.original_ttl = self.refresh_token.expires_in
            self.refresh_token.expires_in = _expires_in
            self.refresh_token.expires_at = datetime.datetime.fromtimestamp(self.refresh_token.claims['exp'],
                                                                            datetime.timezone.utc)
        except:
            pass

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
        if self.account_type == 'service':
            self.x_tenant_id = tenant_id
        self.base_url = base_url

    def upload(self, source_file_path, system_id, dest_file_path, **kwargs):
        """
        Convenience method for uploading a file at a local path to a system
        """
        url = f'{self.base_url}/v3/files/ops/{system_id}/{dest_file_path}'
        # check for the _tapis_debug flag for generating debug data
        debug = False
        if '_tapis_debug' in kwargs:
            debug = kwargs.get('_tapis_debug', False)
            # ignore non-boolean values for the debug flag and set it to False.
            if not type(debug) == bool:
                debug = False
        # construct the http headers -
        headers = {}
        # set the X-Tapis-Token header using the client
        if self.get_access_jwt():
            # check for a token about to expire in the next 5 seconds; assume by default we have a token with
            # plenty of time remaining.
            time_remaining = datetime.timedelta(days=10)
            try:
                time_remaining = self.tapis_client.access_token.expires_in()
            except:
                # it is possible the access_token does not have an expires_in attribute and/or that it is not
                # callable. we just pass on these exceptions and do not try to refresh the token.
                pass
            if datetime.timedelta(seconds=5) > time_remaining:
                # if the access token is about to expire, try to use refresh, unless this is a call to
                # refresh (otherwise this would never terminate!)
                if self.resource_name == 'tokens' and self.operation_id == 'refresh_token':
                    pass
                else:
                    try:
                        self.tapis_client.refresh_tokens()
                    except:
                        # for now, if we get an error trying to refresh the tokens,s, we ignore it and try the
                        # request anyway.
                        pass
            headers = {'X-Tapis-Token': self.get_access_jwt(), }

        headers['Accept'] = 'application/json'
        # the X-Tapis-Tenant and X-Tapis-Username headers can be set when the token represents a service account and the
        # service is making a request on behalf of another user/tenant.
        if self.x_tenant_id:
            headers['X-Tapis-Tenant'] = self.x_tenant_id
        if self.x_username:
            headers['X-Tapis-User'] = self.x_username

        # allow arbitrary headers to be passed in via the special "headers" kwarg -
        try:
            headers.update(kwargs.pop('headers', {}))
        except ValueError:
            raise tapy.errors.InvalidInputError(msg="The headers argument, if passed, must be a dictionary-like object.")

        r = requests.Request('POST',
                             url,
                             files={"file": open(source_file_path, 'rb')},
                             headers=headers).prepare()
        # make the request and return the response object -
        try:
            resp = self.requests_session.send(r, verify=self.verify)
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

        # generate the debug_data object
        debug_data = Debug(request=r, response=resp)
        # get the result's operation ids from the custom x-response-operation-ids for this operation id.from
        # results_operation_ids = [...]
        # resp.headers is a case-insensitive dict
        resp_content_type = resp.headers.get('content-type')
        if hasattr(resp_content_type, 'lower') and resp_content_type.lower() == 'application/json':
            try:
                json_content = resp.json()
            except Exception as e:
                msg = f'Requests could not produce JSON from the response even though the content-type was ' \
                      f'application/json. Exception: {e}'
                # TODO -- should this not be an error if the API has described the content-type as application/json?
                #         what valid use cases do we still have for passing raw content in this case?
                if debug:
                    return resp.content, debug_data
                return resp.content
            # get the Tapis result object which could be a JSON object or list.
            try:
                result = json_content.get('result')
            except Exception as e:
                # some Tapis APIs, such as the Meta API, do not return "result" objects and/or do not return the
                # standard Tapis stanzas but rather "raw" JSON documents
                return resp.content
            if result:
                # if it is a list we should return a list of TapisResult objects:
                if _seq_but_not_str(result):
                    if len([item for item in result if type(item) in TapisResult.PRIMITIVE_TYPES]) > 0:
                        if debug:
                            return TapisResult(result), debug_data
                        return TapisResult(result)
                    else:
                        if debug:
                            return [TapisResult(**x) for x in result], debug_data
                        return [TapisResult(**x) for x in result]
                # otherwise, assume it is a JSON object and return that directly as a result -
                try:
                    if debug:
                        return TapisResult(**result), debug_data
                    return TapisResult(**result)
                except TypeError:
                    # result could be an honest string, in which case the use of **result will result in a type
                    # error, which we catch and then return the result as is.
                    if type(result) == str:
                        return result
                except Exception as e:
                    msg = f'Failed to serialize the result object. Got exception: {e}'
                    raise tapy.errors.InvalidServerResponseError(msg=msg, version=version, request=r, response=resp)
            else:
                # the response was JSON but not the standard Tapis 4 stanzas, so just return the JSON content:
                if debug:
                    return json_content, debug_data
                return json_content

        # todo - note:
        # For now, we do not try to handle other content-types, such as application/xml, etc. We just return
        # the raw content as the result.
        if debug:
            return resp.content, debug_data
        return resp.content



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

        # check for the _tapis_debug flag for generating debug data
        debug = False
        if '_tapis_debug' in kwargs:
            debug = kwargs.get('_tapis_debug', False)
            # ignore non-boolean values for the debug flag and set it to False.
            if not type(debug) == bool:
                debug = False

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
            # check for a token about to expire in the next 5 seconds; assume by default we have a token with
            # plenty of time remaining.
            time_remaining = datetime.timedelta(days=10)
            try:
                time_remaining = self.tapis_client.access_token.expires_in()
            except:
                # it is possible the access_token does not have an expires_in attribute and/or that it is not
                # callable. we just pass on these exceptions and do not try to refresh the token.
                pass
            if datetime.timedelta(seconds=5) > time_remaining:
                # if the access token is about to expire, try to use refresh, unless this is a call to
                # refresh (otherwise this would never terminate!)
                if self.resource_name == 'tokens' and self.operation_id == 'refresh_token':
                    pass
                else:
                    try:
                        self.tapis_client.refresh_tokens()
                    except:
                        # for now, if we get an error trying to refresh the tokens,s, we ignore it and try the
                        # request anyway.
                        pass
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
        # these are the list of allowable request body content types; ex., 'application/json'.
        if hasattr(self.op_desc.request_body, 'content') and hasattr(self.op_desc.request_body.content, 'keys'):
            if 'application/json' in self.op_desc.request_body.content.keys() \
                    or '*/*' in self.op_desc.request_body.content.keys():
                headers['Content-Type'] = 'application/json'
                required_fields = self.op_desc.request_body.content['application/json'].schema.required
                data = {}
                # if the request body has no defined properties, look for a single "request_body" parameter.
                if self.op_desc.request_body.content['application/json'].schema.properties == {}:
                    # choice of "request_body" is arbitrary, as the property name is not provided by the openapi spec in this case
                    data = kwargs['request_body']
                else:
                    # otherwise, the request body has defined properties, so look for each one in the function kwargs
                    for p_name, p_desc in self.op_desc.request_body.content['application/json'].schema.properties.items():
                        if p_name in kwargs:
                            data[p_name] = kwargs[p_name]
                        elif p_name in required_fields:
                            raise tapy.errors.InvalidInputError(msg=f'{p_name} is a required argument.')
                    # serialize data before passing it to the request
                data = json.dumps(data)
            if 'multipart/form-data' in self.op_desc.request_body.content.keys():
                # todo - iterate over parts in self.op_desc.request_body.content['multipart/form-data'].schema.properties
                raise NotImplementedError
        # todo - handle other body content types..

        # create a prepared request -
        # cf., https://requests.kennethreitz.org/en/master/user/advanced/#request-and-response-objects
        r = requests.Request(http_method,
                             url,
                             params=params,
                             data=data,
                             headers=headers).prepare()

        # the create_token operation requires HTTP basic auth, though some services, such as the authenticator, need to
        # use create_token to generate tokens on behalf of other users; in these cases, it is important to not set the
        # BasicAuth header, so we look for a special kwarg in this case
        if self.resource_name == 'tokens' and self.operation_id == 'create_token':
            # look for kwarg, use_basic_auth, to turn off use of BasicAuth; we default this to true so that BasicAuth
            # is used if the argument is not passed.
            if kwargs.get('use_basic_auth', True):
                # construct the requests HTTPBasicAuth header object
                basic_auth_header = requests.auth.HTTPBasicAuth(self.tapis_client.username,
                                                                self.tapis_client.service_password)
                # set the object on the request
                basic_auth_header(r)

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

        # generate the debug_data object
        debug_data = Debug(request=r, response=resp)
        # get the result's operation ids from the custom x-response-operation-ids for this operation id.from
        # results_operation_ids = [...]
        # resp.headers is a case-insensitive dict
        resp_content_type = resp.headers.get('content-type')
        if hasattr(resp_content_type, 'lower') and resp_content_type.lower() == 'application/json':
            try:
                json_content = resp.json()
            except Exception as e:
                msg = f'Requests could not produce JSON from the response even though the content-type was ' \
                      f'application/json. Exception: {e}'
                # TODO -- should this not be an error if the API has described the content-type as application/json?
                #         what valid use cases do we still have for passing raw content in this case?
                if debug:
                    return resp.content, debug_data
                return resp.content
            # get the Tapis result object which could be a JSON object or list.
            try:
                result = json_content.get('result')
            except Exception as e:
                # some Tapis APIs, such as the Meta API, do not return "result" objects and/or do not return the
                # standard Tapis stanzas but rather "raw" JSON documents
                return resp.content
            if result:
                # if it is a list we should return a list of TapisResult objects:
                if _seq_but_not_str(result):
                    if len([item for item in result if type(item) in TapisResult.PRIMITIVE_TYPES]) > 0:
                        if debug:
                            return TapisResult(result), debug_data
                        return TapisResult(result)
                    else:
                        if debug:
                            return [TapisResult(**x) for x in result], debug_data
                        return [TapisResult(**x) for x in result]
                # otherwise, assume it is a JSON object and return that directly as a result -
                try:
                    if debug:
                        return TapisResult(**result), debug_data
                    return TapisResult(**result)
                except TypeError:
                    # result could be an honest string, in which case the use of **result will result in a type
                    # error, which we catch and then return the result as is.
                    if type(result) == str:
                        return result
                except Exception as e:
                    msg = f'Failed to serialize the result object. Got exception: {e}'
                    raise tapy.errors.InvalidServerResponseError(msg=msg, version=version, request=r, response=resp)
            else:
                # the response was JSON but not the standard Tapis 4 stanzas, so just return the JSON content:
                if debug:
                    return json_content, debug_data
                return json_content

        # todo - note:
        # For now, we do not try to handle other content-types, such as application/xml, etc. We just return
        # the raw content as the result.
        if debug:
            return resp.content, debug_data
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


class Debug(object):
    """
    Debug data for an API request.
    """
    def __init__(self, request, response):
        self.request = request
        self.response = response