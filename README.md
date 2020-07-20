# ********* DEPRECATED *********** #

# Use https://github.com/tapis-project/tapipy intead #


# tapy - Tapis V3 Python SDK

Python library for interacting with an instance of the Tapis API Framework.

## Development

This project is under active development, exploring different approaches to SDK generation.
In particular, we have started work on a "dynamic" SDK, located in the ``dyna`` package within the
main ``tapy`` package. See the [docs](tapy/dyna/sketch.md) within that section.  

## Installation

TODO - setup on pypi, e.g., 
```
pip install tapylib
```

## Running the tests
The tests resources are contained within the `test` directory in this repository.  
1. Build the test docker image: `docker build -t tapis/pysdk-tests -f Dockerfile-tests .`
2. Run these tests using the built docker image: `docker run -it --rm  tapis/pysdk-tests`

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
