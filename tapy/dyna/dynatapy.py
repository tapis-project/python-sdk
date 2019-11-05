from collections.abc import Sequence
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


class DynaTapy(object):
    """
    A dynamic client for the Tapis API.
    """
    RESOURCES = ['actors',
                 #'files',
                 'tenants',
                 'tokens',]

    def __init__(self,
                 base_url=None,
                 token=None,
                 x_tenant_id=None,
                 x_username=None,
                 verify=True
                 ):
        # the base_url for the server this Tapis client should interact with
        self.base_url = base_url

        # the JWT to use
        self.token = token

        # use the following two parameters to set headers to make requests on behalf of a different
        # tenant_id and username.
        self.x_tenant_id = x_tenant_id
        self.x_username = x_username

        # whether to verify the TLS certificate at the base_url
        self.verify = verify

        # the requests.Session object this client will use to prepare requests
        self.requests_session = requests.Session()

        # create resources for each API defined above. In the future we could make this more dynamic in multiple ways.
        for resource_name in DynaTapy.RESOURCES:
            try:
                # for now, hardcode the paths; we could look these up based on a canonical URL once that is
                # established.
                spec_path = f'/home/tapis/tapy/dyna/resources/openapi_v3-{resource_name}.yml'
                spec_dict = yaml.load(open(spec_path, 'r'))
                spec = create_spec(spec_dict)
            except Exception as e:
                print("Got exception trying to load spec_path: {spec_path}")
            # each API is a top-level attribute on the DynaTapy object, a Resource object constructed as follows:
            setattr(self, resource_name, Resource(resource_name, spec.paths, self))

    def set_token(self, token):
        """
        Set the token to be used in this session.
        :param token: (str) A valid Tapis JWT.
        :return:
        """
        self.token = token


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
        self.url = f'{self.tapis_client.base_url}/{self.op_desc.path_name}'
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
        url = self.url
        for param in self.path_parameters:
            # look for the name in the kwargs
            if param.required:
                if param.name not in kwargs:
                    raise tapy.errors.InvalidInputError(f"{param.name} is a required argument.")
            p_val = kwargs.pop(param.name)
            if param.required and not p_val:
                raise tapy.errors.InvalidInputError(f"{param.name} is a required argument and cannot be None.")
            # replace the parameter in the path template with the parameter value
            s = '{' + f'{param.name}' + '}'
            url = url.replace(s, p_val)

        # construct the http query parameters -
        params = {}
        for param in self.query_parameters:
            # look for the name in the kwargs
            if param.required:
                if param.name not in kwargs:
                    raise tapy.errors.InvalidInputError(f"{param.name} is a required argument.")
            # only set the parameter if it was actually sent in the function -
            if param.name in kwargs:
                p_val = kwargs.pop(param.name, None)
                params[param.name] = p_val

        # construct the http headers -
        headers = {}

        # set the X-Tapis-Token header using the client
        if hasattr(self.tapis_client, 'token') and self.tapis_client.token:
            headers = {'X-Tapis-Token': self.tapis_client.token, }

        # the X-Tapis-Tenant and X-Tapis-Username headers can be set when the token represents a service account and the
        # service is making a request on behalf of another user/tenant.
        if self.tapis_client.x_tenant_id:
            headers['X-Tapis-Tenant'] = self.tapis_client.x_tenant_id
        if self.tapis_client.x_username:
            headers['X-Tapis-Username'] = self.tapis_client.x_username

        # allow arbitrary headers to be passed in via the special "headers" kwarg -
        try:
            headers.update(kwargs.pop('headers', {}))
        except ValueError:
            raise tapy.errors.InvalidInputError("The headers argument, if passed, must be a dictionary-like object.")

        # construct the data -
        data = None
        # these are the list of allowable request bofy content types; ex., 'application/json'.
        if hasattr(self.op_desc.request_body, 'content') and hasattr(self.op_desc.request_body.content, 'keys'):
            content_types = self.op_desc.request_body.content.keys()
            if 'application/json' in content_types:
                headers['Content-Type'] = 'application/json'
                data = {}
                for p_name, p_desc in self.op_desc.request_body.content['application/json'].schema.properties.items():
                    if p_name in kwargs:
                        data[p_name] = kwargs[p_name]

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
        # for any kind of non-20x response, we need to raise an error.
        if resp.status_code > 399:
            # try to get the error message and version from the Tapis request:
            try:
                error_msg = resp.json().get('message')
            except:
                error_msg = resp.content
            try:
                version = resp.json().get('version')
            except:
                version = None
        if resp.status_code in (400, 404):
            raise tapy.errors.InvalidInputError(msg=error_msg, version=version, request=r, response=resp)
        if resp.status_code in (401, 403):
            raise tapy.errors.NotAuthorizedError(msg=error_msg, version=version, request=r, response=resp)
        if resp.status_code in (500, ):
            raise tapy.errors.ServerDownError(msg=error_msg, version=version, request=r, response=resp)

        # resp.headers is a case-insensitive dict, but the v
        resp_content_type = resp.headers.get('content-type')
        if hasattr(resp_content_type, 'lower') and resp_content_type.lower() == 'application/json':
            try:
                json_content = resp.json()
            except Exception as e:
                msg = f'Requests could not produce JSON from the response even though the content-type was ' \
                      f'application/json. Exception: {e}'
                raise tapy.errors.InvalidServerResponseError(msg=error_msg, version=version, request=r, response=resp)
            # get the Tapis result objectm which could be a JSON object or list.
            result = json_content.get('result')
            # if it is a list we should return a list of TapisResult objects:
            if _seq_but_not_str(result):
                return [TapisResult(**x) for x in result]
            # otherwise, assume it is a JSON object and return that directly as a result -
            return TapisResult(**result)

        # todo - note:
        # For now, we do not try to handle other content-types, such as application/xml, etc. We just return
        # the raw content as the result.
        return resp.content


class TapisResult(object):
    """
    Represents a result returned from a single Tapis operation.
    """

    PRIMITIVE_TYPES = [int, str, bool, bytearray, bytes, None]
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            # for primitive types, we just set the attribute to the value
            if type(v) in TapisResult.PRIMITIVE_TYPES:
                setattr(self, k, v)
            # for lists, we
            elif _seq_but_not_str(v):
                setattr(self, k, [item for item in v])
            # for complex types, we
            else:
                setattr(self, k, TapisResult(v))



