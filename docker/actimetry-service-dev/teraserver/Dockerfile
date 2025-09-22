FROM ubuntu:24.04

# Change default shell to bash
SHELL ["/bin/bash", "-c"]

# Install build dependencies
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y \
    build-essential cmake git sudo vim libprotobuf-dev protobuf-compiler locales wget curl
# Set system locale
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Install miniconda
WORKDIR /root
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash ~/Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3


# Accept Conda Terms of Service for required channels
RUN $HOME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
RUN $HOME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r


# Install latest npm / nodejs
RUN curl -sL https://deb.nodesource.com/setup_18.x -o nodesource_setup.sh
RUN bash ~/nodesource_setup.sh
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs


# Add directory from host
# TODO Use main branch in the future, but need to use dev for now because of bug fixes...
WORKDIR /root
RUN ["/bin/bash", "-c", "touch LAST_UPDATED_02_JUNE_2025_09_00"]
RUN ["/bin/bash", "-c", "git clone -b dev https://github.com/introlab/opentera.git --recurse-submodules"]


# Install node-js signaling server
WORKDIR /root/opentera/teraserver/easyrtc
RUN ["/bin/bash", "-c", "npm install"]

# Build environment
WORKDIR /root/opentera/teraserver
RUN ["/bin/bash", "-c", "cmake ."]
RUN ["/bin/bash", "-c", "make python-all"]

ENV PYTHON3_EXEC=/root/opentera/teraserver/python/env/python-3.11/bin/python3

# Install debugpy
RUN ["/bin/bash", "-c", "$PYTHON3_EXEC -m pip install debugpy"]

# Set Python path
ENV PYTHONPATH=/root/opentera/teraserver/python

# RUN SERVER
WORKDIR /root/opentera/teraserver/python

# RUN SSH SERVER AND TERA SERVER
#CMD ["/bin/bash", "-c", "$PYTHON3_EXEC TeraServer.py"]
#CMD ["/bin/bash", "-c", "trap exit 1 INT; while true; do sleep 1; done"]

# Run in debug mode
CMD ["/bin/bash", "-c", "$PYTHON3_EXEC -m debugpy --listen 0.0.0.0:5679 TeraServer.py --enable_tests=1"]
