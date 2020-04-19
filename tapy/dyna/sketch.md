

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

Note that we are providing the username and password of a valid user account (`testuser1`) 
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
listing (GET endpoint) is available unauthenticated. The DynaTapy constructor retrieved the list of tenants
to resolve the `tenant_id` from the `base_url` passed to the constructor.

In Tapis v3, you don't pass your password directly to each API; instead, you provide an access token. We use the 
`testuser1` credentials to get an access token; technically this is part of the `authenticator` API, but we can use
the `get_tokens()` convenience method:

```
t.get_tokens() 
```
At this point we have an access token, which was returned by the `get_tokens()` method and stored on the
Tapis client, `t`. We can inspect the access token by simply displaying it:

```
type(t.access_token)
Out[*]: tapy.dyna.dynatapy.TapisResult

t.access_token
Out[*]
access_token: eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJqdGkiOiJkODZiZDU2Zi05MTZiLTRhZTQtOTNmYy0wNTViOWE0MDM0MDIiLCJpc3MiOiJodHRwczovL2Rldi5kZXZlbG9wLnRhcGlzLmlvL3YzL3Rva2VuIiwic3ViIjoidGVzdHVzZXIxQGRldiIsInRhcGlzL3RlbmFudF9pZCI6ImRldiIsInRhcGlzL3Rva2VuX3R5cGUiOiJhY2Nlc3MiLCJ0YXBpcy9kZWxlZ2F0aW9uIjpmYWxzZSwidGFwaXMvZGVsZWdhdGlvbl9zdWIiOm51bGwsInRhcGlzL3VzZXJuYW1lIjoidGVzdHVzZXIxIiwidGFwaXMvYWNjb3VudF90eXBlIjoidXNlciIsImV4cCI6MTU4NzI4MDU3MSwidGFwaXMvY2xpZW50X2lkIjpudWxsLCJ0YXBpcy9ncmFudF90eXBlIjoicGFzc3dvcmQifQ.anfFshalxNd8-V1U3GEBnRH2puEV7xgRzRodxinlnuwIl5I7pbHr8tTCFQMSrGP8orq1qDhWRn57L0xsr99PkB36KBkFbO_yaVIoe2v-8hGF0KlYFSYL6mpoes46PFO1EJ9a-tOp9s2uRRlPG-kSTbjvpyf7El73qTi_kZmiRWsX8VJ2grAEFnr5ujt_bx7K3YU4rR6E5IaeTxCP7Qs0wFImJTBrvO41c7nr2PaigBk1UCJtzrv98G_y5Pi4rgpLiY_3cAO7JdI94l_SsMtms8NmkpVsM1jkrcEvvHT1cFzS3eQyqm0qlGR61qcdIYGUlbTMafty08E-vjkZo28a-w
claims: {'jti': 'd86bd56f-916b-4ae4-93fc-055b9a403402', 'iss': 'https://dev.develop.tapis.io/v3/token', 'sub': 'testuser1@dev', 'tapis/tenant_id': 'dev', 'tapis/token_type': 'access', 'tapis/delegation': False, 'tapis/delegation_sub': None, 'tapis/username': 'testuser1', 'tapis/account_type': 'user', 'exp': 1587280571, 'tapis/client_id': None, 'tapis/grant_type': 'password'}
expires_at: 2020-04-19 07:16:11+00:00
expires_in: <function DynaTapy.set_access_token.<locals>._expires_in at 0x7f594da984d0>
jti: d86bd56f-916b-4ae4-93fc-055b9a403402
original_ttl: 14400
```

We see that the `access_token` object is a `TapisResult` object, and when we ask iPython to display it, we get the list
of attributes on the object, in this case `access_token`, `claims`, `expires_at`, `expires_in`, `jti`, `original_ttl`. 
Note that this is typical of all responses from Tapis APIs - assuming the response is a success, the Python SDK 
automatically constructs a `TapisResult` object (or a `list` of `TapisResult` objects) from the
`result` attribute from the response, and each attribute is accessible using the normal object attribute accessor dot
notation; e.g., 
```
t.access_token.jti
Out[*]: 'd86bd56f-916b-4ae4-93fc-055b9a403402'
```  

Note that we do not currently have a refresh token:
```
t.refresh_token
Out[*]: 
```
In order to get an access and refresh token, we also need an OAuth2 client. We do that using the
`authenticator` service.

List our clients:
```
t.authenticator.list_clients()

[
 callback_url: 
 client_id: kGD7eWKE5wdad
 client_key: Ze0YZPV88PAK5
 create_time: Sun, 12 Apr 2020 20:27:54 GMT
 description: 
 display_name: 
 last_update_time: Sun, 12 Apr 2020 20:27:54 GMT
 owner: testuser1
 tenant_id: dev]

```

We already have an OAuth client registered, but if we didn't we could register one using the 
`t.authenticator.create_client()` method, which does not require any arguments (though you can optionally set the
`client_id`, `client_key` and `callback_url` fields). To use a client, simply set the  `client_id` and
`client_key` attributes on your tapis client:

```
t.client_id = 'kGD7eWKE5wdad'
t.client_key = 'Ze0YZPV88PAK5'
```

Now when we call `get_tokens()`, the SDK will automatically use our client credentials and we will be given
an access and refresh token:

```
t.get_tokens()
t.access_token
. . .
jti: 778292c5-1c37-4588-aa13-0d02bf621a6b
. . .

t.refresh_token
. . .
jti: e68c0a0c-4825-4e86-9531-c7014d157572
. . . 
```

## Service Account Type

Tapis v3 introduces the notion of services and "service" account types. These represent the
Tapis v3 API services themselves, such as the Tentants API, Systems APi, Files API, etc.

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
tokens = t.tokens.create_token(account_type='service', token_tenant_id='master', token_username='tenants')
Out[*]: <tapy.dyna.dynatapy.TapisResult at 0x7f699f7ae4e0>

# In general, the result will have both the access and refresh tokens 
tokens.access_token
access_token: eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJqdGkiOiIxZWRjYmJlOC1jYzg3LTQ3NzYtOGY0YS04YzUxNTc3OTgzYTgiLCJpc3MiOiJodHRwczovL21hc3Rlci5kZXZlbG9wLnRhcGlzLmlvL3YzL3Rva2VucyIsInN1YiI6InRlbmFudHNAbWFzdGVyIiwidGFwaXMvdGVuYW50X2lkIjoibWFzdGVyIiwidGFwaXMvdG9rZW5fdHlwZSI6ImFjY2VzcyIsInRhcGlzL2RlbGVnYXRpb24iOmZhbHNlLCJ0YXBpcy9kZWxlZ2F0aW9uX3N1YiI6bnVsbCwidGFwaXMvdXNlcm5hbWUiOiJ0ZW5hbnRzIiwidGFwaXMvYWNjb3VudF90eXBlIjoic2VydmljZSIsImV4cCI6MTU4NzI2ODI2MX0.n4jqD3HfszQ9VvoY_mu12YrBXeuS5OVm7wXjmUf3AUbBGKgzkQLJ_jlLj6_xsaXia992TzdfMbb30XzhEpVu5npXs5baMysM2RLc9PjWxx8jh-jTVCnm0X-HJUTLX3urO6qwtk6jQnNxiRbxlW-9Spav3924QvRjxLqPs3k8FZyzF8dOfNtbqw-Zg2Ju_ejjSY1nBPHcg91RSsykLDp83BrHGTse_Wd9AQGk9ZrtbN2jSEEZF4Uwwyw3dF_KKHV2U7vwVyhmnPyMQqtKi7F6BGFrLWGAXMLos-xmGp5JxnHq_yUewTT4jiiQYbspYBW-CyNJvQx9he8yInfN95HVDg
expires_at: 2020-04-19T03:51:01.294662+00:00
expires_in: 300
jti: 1edcbbe8-cc87-4776-8f4a-8c51577983a8
 
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
