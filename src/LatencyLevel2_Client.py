import socket
import time
import pyshark
import threading
import numpy as np
import mysql.connector
from datetime import datetime
from time import sleep

# Configurazione
SERVER_IP = socket.gethostbyname('server')  # Nome del container server
SERVER_PORT = 5052
TOS = 0x10  # Type of Service (DSCP) -> corrisponde a DSCP 'AF11'
PACKET_COUNT = 4   # Numero di pacchetti da inviare
INTERFACE = "eth0"  # Interfaccia di rete del container

# Configurazione DB
DB_CONFIG = {
    "host": "database",
    "port": "3306",
    "user": "user",
    "password": "test",
    "database": "network_performance"
}

# Array per i timestamp di uscita (client) e ricezione (server)
client_timestamps = []
server_timestamps = []


def send_packets():
    """Invia pacchetti UDP con TOS personalizzato."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Usa UDP
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, TOS)   # Imposta DSCP/TOS

    for i in range(PACKET_COUNT):
        packet = f"PKT_{i}".encode()
        sock.sendto(packet, (SERVER_IP, SERVER_PORT))
        print(f"Inviato PKT_{i}")
        time.sleep(0.0001)  # Spaziatura tra pacchetti in seconfi


def sniff_packets():
    """Cattura i pacchetti in uscita e registra i timestamp."""
    # pyshark usa il filtro display di Wireshark: ip.dsfield == TOS decimal
    capture = pyshark.LiveCapture(interface=INTERFACE, display_filter=f"ip.dsfield.dscp == 4 and ip.dst == {SERVER_IP}")
    for packet in capture.sniff_continuously():
        if hasattr(packet, 'ip'):
            client_timestamps.append(float(packet.sniff_timestamp))
            print(f"Sniffato pacchetto alle {packet.sniff_timestamp}")
            if len(client_timestamps) == PACKET_COUNT:
                break


def receive_server_timestamps():
    """Riceve i tempi di arrivo dal server sulla porta TCP 5051"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)  # Timeout di 5 secondi
                print(f"Connessione al server {SERVER_IP}:5052...")
                s.connect((SERVER_IP, 5053))  # Porta TCP per i timestampDIVERSA!!!
                data = s.recv(4096).decode()
                server_timestamps.extend(list(map(float, data.split(','))))
                print(f"Ricevuti {len(server_timestamps)} timestamp dal server")
                return  # Successo, esci
        except Exception as e:
            print(f"Tentativo {attempt+1}/{max_retries} fallito: {str(e)}")
            time.sleep(1)
    print("Errore: impossibile ricevere i timestamp")


def calculate_metrics():
    """Calcola latenza e jitter."""
    print('client')
    print(client_timestamps)
    print ('server')
    print(server_timestamps)
    #latencies = np.array(client_timestamps[1:PACKET_COUNT]) - np.array(server_timestamps)
    latencies = np.array(server_timestamps)-np.array(client_timestamps[0:PACKET_COUNT-1])
    latency_ms = np.mean(latencies) * 1000
    jitter_ms = np.std(latencies) * 1000

    print(f"Latenza media: {latency_ms:.2f} ms")
    print(f"Jitter: {jitter_ms:.2f} ms")

    # Salva nel DB
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO LatencyLevel2 (jitter_ms, latency_ms, public_ip, private_ip, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, (jitter_ms, latency_ms, "8.8.8.8", socket.gethostbyname(SERVER_IP), datetime.now()))
    conn.commit()
    conn.close()


def sync_clock_with_server():
    """Sincronizza il clock del client con il server, stima offset"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            T1 = time.time()
            s.connect((SERVER_IP, 5051))
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
    # Avvia sniffing in background
    sniff_thread = threading.Thread(target=sniff_packets, daemon=True)
    sniff_thread.start()
    sleep(3)
    # Invia pacchetti
    send_packets()
    sleep(3)
    # Ricevi tempi dal server
    receive_server_timestamps()
    sleep(7)
    client_timestamps[:] = [ts + offset for ts in client_timestamps]
    # Calcola metriche
    calculate_metrics()