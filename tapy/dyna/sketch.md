# Usage

```bash

from tapy.dyna.dynatapy import DynaTapy
t = DynaTapy(base_url='http://tenants:5000', token='some_jwt')

# inspect the resources and the operations -
t.tenants...

t.tokens...
```

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

The libaray handles validation or required parameters:

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