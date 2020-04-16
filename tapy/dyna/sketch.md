

# Usage

The following examples illustrate the use of `DynaTapy`, a "dynamically" generated Python
client for the Tapis v3 API. For information on the architecutre and technical approach this
project takes, see the architecture.md document.  


## Interact with the Develop Instance

Create a client for a user account in the dev tenant of the develop environment:
```
from tapy.dyna import DynaTapy 
t = DynaTapy(base_url='https://dev.develop.tapis.io', username='testuser1', password='testuser1') 
```

Note that we are providing the username and password of a valid user account (`testuser`) 
for the develop tenant. However, those fields were optional. We could have created the Tapis
client without the username or the password with the plan to add them later, for example:
```
t = DynaTapy(base_url='https://dev.develop.tapis.io')

# do some work, maybe prompt the user for their credentials or get them from a config...

# set them once we are ready:
t.username = username
t.password = password
```

You won't be able to do much without credentials, but you will notice that the `tenant_id` attribute on the DynaTapy 
client got set:
```
t = DynaTapy(base_url='https://dev.develop.tapis.io')
t.tenant_id
Out[*]: 'dev'
```
In v3, the Tenants API is a first-class service that maintains the registry of all tenants, and the 
listing (GET endpoint) is available DynaTapy constructor used on


In Tapis v3, you don't pass your password directly to each API; instead, you provide an access token. We use the testuser1 
credentials to get an access token; technically this is part of the `oauth2` API, but we can use
the `get_tokens()` convenience method. 

Create a client for a service to the develop environment.

```bash
from tapy.dyna import DynaTapy
t = DynaTapy(base_url='https://master.develop.tapis.io', username='tenants', account_type='service', tenant_id='master')
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

## A Survey of the Tapis v3 Services (Under Construction)
In this section, we'll walk through some of the APIs available in the Tapis v3 develop environment. For what follows, 
we will be making use of the following "user" client in the dev tenant:

```
from tapy.dyna import DynaTapy  
t = DynaTapy(base_url='https://dev.develop.tapis.io', username='testuser1', password='testuser1')  
```

We can list systems and get a system by name:

```
t.systems.getSystemNames() 
Out[*]: names: ['KDevSystem1', 'testFilesLs2']

t.systems.getSystemByName(sysName='testFilesLs2')
Out[*}:
accessCredential: None
bucketName: myBucket
created: 2020-01-22T17:56:28.564234Z
defaultAccessMethod: PASSWORD
description: Default system for files ls test
effectiveUserId: root
enabled: True
host: localhost
id: 3
jobCanExec: False
. . .
```

We can create a new system from a JSON file description:
```
import json
with open('resource_examples/system-example.json', 'r') as f:
    system_description = json.loads(f.read())

t.systems.createSystem(tSystem=system_description['tSystem'])
```


# Working with Tapis Services Running Locally 
The following assumes the tenants and tokens APIs have been started using the dev stack in
the `test` directory.

```bash

from tapy.dyna import DynaTapy
t = DynaTapy(base_url='http://nginx')

# inspect the resources and the operations -
t.tenants...

t.tokens...
```
