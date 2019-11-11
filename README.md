# tapy - Tapis V3 Python SDK

Python library for interacting with an instance of the Tapis API Framework.

## Installation

TODO - setup on pypi, e.g., 
```
pip install tapylib
```

## Usage

TODO - provide working examples, e.g., 
```
import tapy
t = tapy.Tapis(base_url='http://localhost:5001')
req = t.tokens.NewTokenRequest(token_type='service', token_tenant_id='dev', token_username='admin')
t.tokens.create_token(req)

import openapi_client
configuration = openapi_client.Configuration()
configuration.host = 'http://localhost:5001'
api_instance = openapi_client.TokensApi(openapi_client.ApiClient(configuration))

new_token = openapi_client.NewTokenRequest(token_type='service', token_tenant_id='dev', token_username='admin')

resp = api_instance.create_token(new_token)
jwt = resp.get('result').get('access_token').get('access_token')
```

## Development

We have started work on a "dynamic" SDK, located in the ``dyna`` package within the
main ``tapy`` package. See the [docs](tapy/dyna/sketch.md) within that section.  