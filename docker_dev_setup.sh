#!/bin/bash
mkdir -p /build-docker
cd /build-docker
cmake ../actimetry-service -DCMAKE_BUILD_TYPE=Release -DPYTHON_ENV_DIRECTORY=/root/miniconda3/envs/actimetry-env
# Generate translations
make opentera-actimetry-service-python-all-with-translations-compile-only
