import requests
from openapi_core import create_spec
import yaml

import tapy.errors


class DynaTapy(object):
    """
    A dynamic client for the Tapis API.
    """
    RESOURCES = ['tenants', 'tokens']

    def __init__(self,
                 base_url=None,
                 x_tenant_id=None,
                 x_username=None
                 ):
        self.base_url = base_url
        self.x_tenant_id = x_tenant_id
        self.x_username = x_username
        self.requests_session = requests.Session()
        for resource_name in DynaTapy.RESOURCES:
            try:
                spec_path = f'/home/tapis/tapy/dyna/resources/openapi_v3-{resource_name}.yml'
                spec_dict = yaml.load(open(spec_path, 'r'))
                spec = create_spec(spec_dict)
            except Exception as e:
                print("Got exception trying to load spec_path: {spec_path}")
            setattr(self, resource_name, Resource(resource_name, spec.paths, self))


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
        self.path_parameters = op_desc.parameters
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

        # contruct the http path -
        base_url = self.tapis_client.base_url
        # todo - add path parameters
        url = f'{base_url}/{self.resource_name}'

        # contruct the data -
        # todo --
        data = None

        # construct the http headers -
        # allow arbitrary headers to be passed into the
        headers = {'X-Tapis-Token': self.tapis_client.token, }

        # the X-Tapis-Tenant and X-Tapis-Username headers can be set when the token represents a service account and the
        # service is making a request on behalf of another user/tenant.
        if self.tapis_client.x_tenant_id:
            headers['X-Tapis-Tenant'] = self.tapis_client.x_tenant_id
        if self.tapis_client.x_username:
            headers['X-Tapis-Username'] = self.tapis_client.x_username

        try:
            headers.update(kwargs.pop('headers', {}))
        except ValueError:
            raise tapy.errors.InvalidInputError("The headers argument, if passed, must be a dictionary-like object.")

        # create a prepared request -
        r = requests.Request(http_method, url, data=data, headers=headers).prepare()

        # return the response object -
        try:
            # todo - the tapis_client.requests_session should be a request.Session object;
            #        cf., https://requests.kennethreitz.org/en/master/user/advanced/#request-and-response-objects
            resp = self.tapis_client.requests_session.send(r)
            resp.raise_for_status()
            # todo - deserialize response
            return resp
        except Exception as e:
            # todo - handle exceptions
            raise e



