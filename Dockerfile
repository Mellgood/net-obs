# Dockerfile
FROM ubuntu:22.04

# Install basic utilities, iperf3, and network tools
RUN apt-get update && apt-get install -y \
    nano \
    vim \
    iputils-ping \
    dnsutils \
    curl \
    iperf3 \
    iproute2 \
    net-tools \
    python3 \
    python3-pip \
     \
    #python3 -m pip install mysql-connector-python \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install mysql-connector-python requests
ENV PYTHONUNBUFFERED=1
#RUN python3 --version
# Imposta la directory di lavoro
WORKDIR /app

# Copia i file dalla directory locale src nel container
COPY ./src/ .

# Comando di default per eseguire il tuo script Python
#CMD ["python3", "main.py"]