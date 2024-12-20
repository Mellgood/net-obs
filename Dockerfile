# Dockerfile
FROM ubuntu:latest

# Install basic utilities, iperf3, and network tools
RUN apt-get update && apt-get install -y \
    iputils-ping \
    dnsutils \
    curl \
    iperf3 \
    iproute2 \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR app

COPY ./src/ .

# Set default command
CMD ["bash"]
