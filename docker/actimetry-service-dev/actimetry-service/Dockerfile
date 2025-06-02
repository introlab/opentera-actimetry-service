FROM ubuntu:24.04
# Change default shell to bash
SHELL ["/bin/bash", "--login", "-c"]

# Install build dependencies
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y \
	build-essential git sudo vim  locales wget curl cmake

# Set system locale
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR /

# Install miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash ./Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

# Copy requirements file (does not change often)
ADD ./requirements.txt requirements.txt

# Create conda venv in local directory outside of sources
RUN $HOME/miniconda3/bin/conda create -c conda-forge -y --copy -n actimetry-env python=3.11
RUN $HOME/miniconda3/bin/conda init bash

# Make RUN commands use the new environment:
SHELL ["/root/miniconda3/bin/conda", "run", "-n", "actimetry-env", "/bin/bash", "-c"]

# NOTE: Next run commands will have bash + conda + venv initialized properly
# Debug, print python version and path
RUN python3 --version
RUN which python3

# Install Python dependencies
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install debugpy

## RUN Servic
WORKDIR /actimetry-service

ENV PYTHONPATH=/actimetry-service
ENV PYTHON3_EXEC=/root/miniconda3/envs/actimetry-env/bin/python3

# Will keep the container running and update translations.
CMD ["/bin/sh", "-c", "./docker_dev_setup.sh; trap exit 1 INT; while true; do sleep 1; done"]


# The service will restart until DB is configured...
# CMD ["/bin/bash", "-c", "./docker_dev_setup.sh; $PYTHON3_EXEC tools/create_actimetry_service.py; $PYTHON3_EXEC -m debugpy --listen 0.0.0.0:5678 actimetryService.py"]
