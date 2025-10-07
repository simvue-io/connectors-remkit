FROM smijin/remkit1d-ci:latest

# Disable Prompt During Packages Installation
ARG DEBIAN_FRONTEND=noninteractive

RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test

# # Update and Install Required Packages for Simvue and other Packages
RUN apt update \
        && apt install -y \
        pip vim nano

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN pip install uv

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

# While it is private, comment out this clone
RUN git clone https://github.com/simvue-io/connectors-remkit
WORKDIR /home/connectors-remkit
# And uncomment this copy
# COPY . .
RUN uv venv --python 3.11
RUN uv pip install .

ENV VIRTUAL_ENV=/home/connectors-remkit/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

