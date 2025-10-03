FROM smijin/remkit1d-ci:latest

# Disable Prompt During Packages Installation
ARG DEBIAN_FRONTEND=noninteractive

RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
RUN add-apt-repository ppa:deadsnakes/ppa

# Update and Install Required Packages for Simvue and other Packages
RUN apt update \
        && apt install -y \
        python3.11 python3.11-venv python3.11-dev \
        pip

RUN apt install -y vim nano

RUN ln -s /usr/bin/python3.11 /usr/bin/python

RUN python3.11 -m ensurepip --upgrade \
    && python3.11 -m pip install --upgrade pip setuptools wheel

WORKDIR /home

# Install ReMKiT1D
RUN git clone -b master https://github.com/ukaea/ReMKiT1D.git

WORKDIR /home/ReMKiT1D 

RUN mkdir debug && cd debug && cmake .. && make -j 

# Test ReMKiT1D 

WORKDIR /home/ReMKiT1D/debug

RUN make test > /home/ReMKiT1D_debug_test.out

WORKDIR /home/ReMKiT1D 

RUN mkdir build && cd build && cmake .. && make -j 

WORKDIR /home/ReMKiT1D/build

RUN make test > /home/ReMKiT1D_build_test.out

WORKDIR /home

RUN git clone https://github.com/simvue-io/connectors-remkit

WORKDIR /home/connectors-remkit/

RUN python3.11 -m pip install .

WORKDIR /home/connectors-remkit/examples

