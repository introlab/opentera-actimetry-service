FROM python:3.11-bullseye
# Install build dependencies
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y \
	build-essential cmake git
# Add directory from host

# TODO use main branch in the future, but need to use dev for now because of bug fixes...
WORKDIR /
RUN ["/bin/bash", "-c", "git clone -b dev https://github.com/introlab/opentera.git --recurse-submodules"]


RUN ls -l ./opentera/teraserver
RUN pip install -r ./opentera/teraserver/python/env/requirements.txt
# Generate certificates
WORKDIR /opentera/teraserver/python

# Will create the certificates (if required) and keep the container running.
CMD ["/bin/sh", "-c", "python ./CreateCertificates.py; trap exit 1 INT; while true; do sleep 1; done"]
