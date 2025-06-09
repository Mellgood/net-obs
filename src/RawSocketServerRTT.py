import socket
import time
import json
from datetime import datetime
import mysql.connector

# Configurazione DB (usa la stessa del client)
DB_CONFIG = {
    "host": "database",
    "port": "3306",
    "user": "user",
    "password": "test",
    "database": "network_performance"
}

# Configurazione rete
CLIENT_IP = "client"
CLIENT_PORT = 5002
SERVER_PORT = 5001
PACKET_INTERVAL = 1
NUM_PACKETS = 10


def get_timezone_offset():
    """Restituisce il fuso orario locale in secondi."""
    local_tz = datetime.now().astimezone().tzinfo
    return int(local_tz.utcoffset(None).total_seconds())


def save_rtt_data(rtt_values, jitter, public_ip, private_ip):
    """Salva i dati RTT nel database."""
    if not rtt_values:
        return

    avg_rtt = sum(rtt_values) / len(rtt_values)

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        query = """
            INSERT INTO RTT_test 
            (jitter_ms, latency_ms, public_ip, private_ip, timestamp)
            VALUES (%s, %s, %s, %s, NOW())
        """
        # Usiamo avg_rtt come latency_ms e jitter come jitter_ms
        cursor.execute(query, (jitter, avg_rtt, public_ip, private_ip))
        connection.commit()

        print(f"Dati salvati nel database - RTT medio: {avg_rtt:.6f} ms, Jitter: {jitter:.6f} ms")
    except Exception as e:
        print(f"Errore durante il salvataggio nel database: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def get_public_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "unknown"


def send_and_receive_udp_packets():
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("0.0.0.0", SERVER_PORT))

    rtt_values = []
    print("Avvio misurazione RTT...")

    for i in range(NUM_PACKETS):
        # Invio pacchetto
        send_time = time.time()
        packet_data = {
            "seq": i + 1,
            "send_timestamp": send_time,
            "timezone_offset": get_timezone_offset()
        }
        send_sock.sendto(json.dumps(packet_data).encode(), (CLIENT_IP, CLIENT_PORT))

        # Ricezione risposta
        try:
            recv_sock.settimeout(2)
            data, addr = recv_sock.recvfrom(1024)
            recv_time = time.time()

            response = json.loads(data.decode())
            if response.get("seq") == i + 1:
                rtt = (recv_time - send_time) * 1000
                rtt_values.append(rtt)
                print(f"Pacchetto {i + 1} - RTT: {rtt:.6f} ms")

        except socket.timeout:
            print(f"Timeout per il pacchetto {i + 1}")

        time.sleep(PACKET_INTERVAL)

    # Calcolo statistiche e salvataggio
    if rtt_values:
        jitter = max(rtt_values) - min(rtt_values)
        public_ip = get_public_ip()
        private_ip = socket.gethostbyname(socket.gethostname())
        save_rtt_data(rtt_values, jitter, public_ip, private_ip)

    send_sock.close()
    recv_sock.close()


if __name__ == "__main__":
    send_and_receive_udp_packets()
    print("Misurazione completata.")