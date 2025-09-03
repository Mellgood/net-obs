import socket
import time
import pyshark
import threading
import numpy as np
import mysql.connector
from datetime import datetime
from time import sleep
import os
IP=socket.gethostbyname('server')
# Configurazione
SERVER_IP = os.getenv('SERVER_IP', IP)  # IP pubblico del server su AWS
SERVER_UDP_PORT = 5052
SERVER_TCP_TIMESTAMP_PORT = 5053
SERVER_CLOCKSYNC_PORT = 5051
TOS = 0x10
PACKET_COUNT = 5
INTERFACE = "eth0"

# Configurazione DB
DB_CONFIG = {
    "host": "database",
    "port": "3306",
    "user": "user",
    "password": "test",
    "database": "network_performance"
}

client_timestamps = []
server_timestamps = []

def send_packets():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, TOS)
    for i in range(PACKET_COUNT):
        packet = f"PKT_{i}".encode()
        sock.sendto(packet, (SERVER_IP, SERVER_UDP_PORT))
        print(f"[Client] Inviato PKT_{i}")

def sniff_packets():
    capture = pyshark.LiveCapture(interface=INTERFACE, display_filter=f"ip.dsfield.dscp == 4 and ip.dst == {SERVER_IP}")
    for packet in capture.sniff_continuously():
        if hasattr(packet, 'ip'):
            client_timestamps.append(float(packet.sniff_timestamp))
            print(f"[Client] Sniffato alle {packet.sniff_timestamp}")
            if len(client_timestamps) == PACKET_COUNT:
                break

def receive_server_timestamps():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                print(f"[Client] Connessione al server {SERVER_IP}:{SERVER_TCP_TIMESTAMP_PORT}...")
                s.connect((SERVER_IP, SERVER_TCP_TIMESTAMP_PORT))
                data = s.recv(4096).decode()
                server_timestamps.extend(map(float, data.split(',')))
                print(f"[Client] Ricevuti {len(server_timestamps)} timestamp")
                return
        except Exception as e:
            print(f"[Client] Tentativo {attempt+1}/{max_retries} fallito: {e}")
            time.sleep(1)
    print("[Client] Errore: impossibile ricevere i timestamp")

def calculate_metrics():
    print('[Client] Timestamp locali:', client_timestamps)
    print('[Client] Timestamp server:', server_timestamps)
    #latencies = np.array(server_timestamps) - np.array(client_timestamps[0:PACKET_COUNT])
    latencies = np.array(client_timestamps[1:PACKET_COUNT]) - np.array(server_timestamps[1:PACKET_COUNT])
    latency_ms = np.mean(latencies) * 1000
    jitter_ms = np.std(latencies) * 1000
    print(f"[Client] Latenza media: {latency_ms:.2f} ms | Jitter: {jitter_ms:.2f} ms")

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO LatencyLevel2 (jitter_ms, latency_ms, public_ip, private_ip, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, (jitter_ms, latency_ms, "8.8.8.8", socket.gethostbyname(SERVER_IP), datetime.now()))
    conn.commit()
    conn.close()

def sync_clock_with_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            T1 = time.time()
            s.connect((SERVER_IP, SERVER_CLOCKSYNC_PORT))
            data = s.recv(1024).decode()
            T4 = time.time()
            T_server = float(data)
            estimated_offset = T_server - ((T1 + T4) / 2)
            print(f"[ClockSync] Offset stimato: {estimated_offset:.6f} s")
            return estimated_offset
    except Exception as e:
        print(f"[ClockSync] Errore: {e}")
        return 0.0

if __name__ == "__main__":
    offset = sync_clock_with_server()
    sniff_thread = threading.Thread(target=sniff_packets, daemon=True)
    sniff_thread.start()
    sleep(3)
    send_packets()
    sleep(3)
    receive_server_timestamps()
    sleep(7)
    #client_timestamps[:] = [ts + offset for ts in client_timestamps]
    calculate_metrics()
