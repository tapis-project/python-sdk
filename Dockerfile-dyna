# Image: tapis/dynatapy
# Build: docker build -t tapis/dynatapy -f Dockerfile-dyna .
# Try it:
#    docker run -it --rm tapis/dynatapy bash
#    docker run -it --rm -v $(pwd)/test/resource_examples:/home/tapis/resource_examples tapis/dynatapy bash
#    docker run -it --network tenants-api_tenants --rm tapis/dynatapy bash

from tapis/flaskbase

USER root
ADD tapy/dyna/requirements.txt /home/tapis/requirements.txt
RUN pip install -r /home/tapis/requirements.txt

ADD test/configschema.json /home/tapis/configschema.json
ADD test/config-dev-develop.json /home/tapis/config.json

ADD tapy /home/tapis/tapy

RUN chown -R tapis:tapis /home/tapis
USER tapis
