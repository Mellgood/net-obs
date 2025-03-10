import socket
import struct
import time
import json
import mysql.connector
import requests
from datetime import datetime


# Configurazione del database
DB_CONFIG = {
    "host": "database",
    "port": "3306",
    "user": "user",
    "password": "test",
    "database": "network_performance"
}

UDP_PORT = 5000
PACKET_SIZE = 1024
PACKET_LIMIT = 10  # Numero di pacchetti da raccogliere prima di fermarsi

def get_public_ip():
    try:
        response = requests.get("https://api64.ipify.org?format=json")
        return response.json()["ip"]
    except Exception:
        return "Impossibile determinare l'IP pubblico"

def get_private_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "Impossibile determinare l'IP privato"

def save_jitter_latency(latencies, ip_public, ip_private):
    if len(latencies) < 2:
        return  # Non possiamo calcolare il jitter con un solo valore

    avg_latency = sum(latencies) / len(latencies)
    jitter = max(latencies) - min(latencies)

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    query = """
        INSERT INTO jitter_latency (jitter_ms, latency_ms, public_ip, private_ip, timestamp)
        VALUES (%s, %s, %s, %s, NOW())
    """
    cursor.execute(query, (jitter, avg_latency, ip_public, ip_private))
    connection.commit()
    cursor.close()
    connection.close()

    print(f" Dati salvati nel database - Latenza: {avg_latency:.6f} ms, Jitter: {jitter:.6f} ms")

def raw_socket_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
    sock.bind(("0.0.0.0", UDP_PORT))
    latencies = []
    print(f"In attesa di {PACKET_LIMIT} pacchetti UDP per calcolare latenza e jitter...")

    while len(latencies) < PACKET_LIMIT:
        raw_data, addr = sock.recvfrom(PACKET_SIZE)
        received_time = time.time()
        # Estrazione payload dopo header IP e UDP
        ip_header_len = (raw_data[0] & 0x0F) * 4
        udp_header_len = 8
        payload_offset = ip_header_len + udp_header_len
        payload = raw_data[payload_offset:]
        try:
            payload_str = payload.decode("utf-8")
            packet = json.loads(payload_str)
            seq = packet.get("seq")
            sent_time = packet.get("timestamp")
            latency = (received_time - sent_time)*1000
            latencies.append(latency)
            print(f"Pacchetto {seq} ricevuto - Latenza: {latency:.6f} ms")
        except Exception as e:
            print(f"Errore nella decodifica del pacchetto: {e}")

    ip_public = get_public_ip().strip()
    ip_private = get_private_ip().strip()
    save_jitter_latency(latencies, ip_public, ip_private)
if __name__ == "__main__":
    raw_socket_client()
