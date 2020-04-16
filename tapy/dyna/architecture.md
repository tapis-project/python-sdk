# DynaTapy Architecture

The dynamic approach to SDK generation relies on a hierarchy of three classes:
  * DynaTapy - this is the actual client that end-users instantiate. Multiple "resources" hang off of this client.
  * Resource - resource instances correspond to a top-level Tapis API resource, such as Systems, Files, Tokens, Authenticator, etc.
  * Operation - operations correspond to specific endpoints (HTTP URL + verb) with a resource. Technically speaking, 
  they correspond to verb within a "path" object in the spec file and show have a unique "operationId" field. Operations 
  are attached to a specific resource object.
  
Thus, if we have code that instantiates a `DynaTapy` client such as:
```
t = DynaTapy(base_url='https://dev.develop.tapis.io')
```

then, `t` is a `DynaTapy` with multiple resource objects attached to it as top level objects corresponding to the APIs 
supported -- `actors`, `authenticator`, `files`, `meta`, etc. Then, for each resource there are multiple operations 
which are "callables" (i.e., class methods) attached to each resource. For example: the `actors` resource has operations
such as: `list_actors()`, `create_actor()`, `get_actor()`, etc. In code, we could do something like:
```
t.actors.list_actors()
```

## High Level Description of DynaTapy Constructor Algorithms

When the `DynaTapy()` constructor is called, the following algorithm runs:

1. Set attributes on the instance based on parameters passed to the constructor.
2. For each resource in the defined resource list constant, create a "resource_spec" object from a 
"raw yaml dictionary" for the API using the `create_spec()` function from the `openapi_core` library. The resource_spec 
object provides structured access to various aspects of the spec. It is worth noting the `create_spec()` call will fail 
if the spec does not validate. The source of the "raw yaml dictionary" is either:
    1. Reading the corresponding openapi_v3.yml file included in the repo for the resource OR
    2. Downloading the "latest" openapi_v3.yml file from the corresponding github repository.
3. For each resource object corresponding to a resource in the list, create a Resource() instance.

When the `Resource()` constructor is called, the following algorithm is used:

1. Set convenience attributes on the object coming from the spec object, including the `resource_spec` itself and the 
`tapis_client`. 
2. For each `path` in the paths list do:
    For each `operation_id` in the the `path` do:
      a. create an `Operation` object
      b. set the `Operation` object as an attribute on the resource object with attribute name equal to the `operation_id.`    

