

# Usage

The following examples illustrate the use of `DynaTapy`. They assume
the tenants and tokens APIs have been started using the dev stack in
the `test` directory.

```bash

from tapy.dyna.dynatapy import DynaTapy
t = DynaTapy(base_url='http://nginx')

# inspect the resources and the operations -
t.tenants...

t.tokens...
```

## Interact with the Develop Instance

Create a client pointing to the develop environment.

```bash

t = DynaTapy(base_url='https://dev.develop.tapis.io', token_username='tenants', account_type='service', token_tenant_id='dev')
t.get_tokens()
t.access_token.expires_at                                                                           
Out[*]: '2019-11-12 16:57:48.982899'
```

## Results

When you call a function, the result returned is a `TapisResult` or a `list[TapisResult]`
```
# get the list of tenants, we expect a python list:
t.tenants.list_tenants()                                                             
Out[*]: [<tapy.dyna.dynatapy.TapisResult at 0x7f156d806240>]

# TapisResult objects have attributes corresponding to the returned attributes:   
tenants = t.tenants.list_tenants()
first_tenant = tenants[0]
first_tenant.base_url                                                               
Out[*]: 'https://api.tacc.utexas.edu'

first_tenant.tenant_id
Out[*]: 'tacc'

first_tenant.create_time
Out[*]: 'Mon, 04 Nov 2019 20:09:18 GMT'
```

## Validation
The library handles validation or required parameters:

```
# the getTenant method requires tenant_id:
t.tenants.getTenant()                                                                
---------------------------------------------------------------------------
InvalidInputError                         Traceback (most recent call last)
<ipython-input-22-ea1c896eccf7> in <module>
----> 1 t.tenants.getTenant()

~/tapy/dyna/dynatapy.py in __call__(self, **kwargs)
    153             if param.required:
    154                 if param.name not in kwargs:
--> 155                     raise tapy.errors.InvalidInputError(f"{param.name} is a required argument.")
    156             p_val = kwargs.pop(param.name)
    157             if param.required and not p_val:

InvalidInputError: tenant_id is a required argument.
```

## Exceptions

DynaTapy Exceptions come with some attributes that are useful for debugging: 

```
# try to create a tenant without an authentication token - 
try: 
    t.tenants.create_tenant() 
except Exception as e: 
    err = e 

# the error message returned by the API:
err.message                                                                               
Out[*]: 'No Tapis access token found in the request.'

# the version returned by the API: 
err.version                                                                           
Out[*]: 'dev'

# inspect the original request that DynaTapy sent:
err.request                                                                           
Out[*]: <PreparedRequest [POST]>

# oops - no token header, but that wasn't DynaTapy's fault!
err.request.headers                                                                   
Out[*]: {'Content-Type': 'application/json', 'Content-Length': '0'}

# inspect the full Tapis API response object returned as well:
err.response                                                                          
Out[*]: <Response [400]>

err.response.content                                                                  
Out[*]: b'{"message":"No Tapis access token found in the request.","result":null,"status":"error","version":"dev"}\n'

```


## Authenticated Requests
Get a token, set the token, create a tenant:

```
# Get a new token:
tokens = t.tokens.create_token(token_type='service', token_tenant_id='dev', token_username='admin')
Out[*]: <tapy.dyna.dynatapy.TapisResult at 0x7f699f7ae4e0>

# In general, the result will have both the access and refresh tokens 
tokens.access_token

tenant = {'tenant_id': 'dev',
 'base_url': 'https://dev.develop.tapis.io',
 'description': 'The dev tenant in the develop instance.',
 'token_service': 'https://dev.develop.tapis.io/v3/tokens',
 'security_kernel': 'https://dev.develop.tapis.io/v3/security',
 'is_owned_by_associate_site': True,
 'owner': 'jstubbs@tacc.utexas.edu',
 'authenticator': 'https://dev.develop.tapis.io/v3/oauth3',
 'allowable_x_tenant_ids': ['dev']
 }
 
 ```