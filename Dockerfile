# Dockerfile per container client con tutte le dipendenze
FROM ubuntu:22.04
# 1. Configurazione repository e pacchetti base
RUN sed -i 's|http://archive.ubuntu.com|http://it.archive.ubuntu.com|g' /etc/apt/sources.list && \
    apt-get update -qy && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    tshark \
    wireshark-common \
    python3 \
    python3-pip \
    python3-numpy \
    nano \
    iputils-ping \
    dnsutils \
    curl \
    iperf3 \
    iproute2 \
    net-tools \
    ntp \
    && rm -rf /var/lib/apt/lists/*

#ENV IP =

# 2. Configurazione Wireshark
RUN echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections && \
    dpkg-reconfigure -f noninteractive wireshark-common && \
    usermod -aG wireshark root

# 3. Installazione dipendenze Python
RUN python3 -m pip install --no-cache-dir \
    mysql-connector-python \
    requests \
    python-socketio \
    pyshark \
    numpy \
    ntplib

# 4. Variabili d'ambiente
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 5. Copia gli script
COPY ./src/ .

# 6. Permessi aggiuntivi
RUN chmod +x /app/LatencyLevel2_Client.py

# 7. Permessi necessari per dumpcap
RUN apt-get update && \
    apt-get install -y libcap2-bin && \
    chmod +x /usr/bin/dumpcap && \
    chgrp wireshark /usr/bin/dumpcap && \
    chmod 750 /usr/bin/dumpcap && \
    setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap