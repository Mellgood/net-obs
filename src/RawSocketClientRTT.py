import socket
import time
import json
import mysql.connector
import requests

DB_CONFIG = {
    "host": "database",
    "port": "3306",
    "user": "user",
    "password": "test",
    "database": "network_performance"
}

UDP_PORT = 5002
SERVER_PORT = 5001  # Porta del server per le risposte
PACKET_SIZE = 1024
PACKET_LIMIT = 10


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


def save_rtt_data(rtt_values, ip_public, ip_private):
    if not rtt_values:
        return
    avg_rtt = sum(rtt_values) / len(rtt_values)
    jitter = max(rtt_values) - min(rtt_values)
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    query = """
            INSERT INTO rtt_measurements (avg_rtt_ms, jitter_ms, public_ip, private_ip, timestamp)
            VALUES (%s, %s, %s, %s, NOW())
        """
    cursor.execute(query, (avg_rtt, jitter, ip_public, ip_private))
    connection.commit()
    cursor.close()
    connection.close()

    print(f"Dati salvati nel database - RTT medio: {avg_rtt:.6f} ms, Jitter: {jitter:.6f} ms")


def rtt_client():
    # Socket per ricevere i pacchetti
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind(("0.0.0.0", UDP_PORT))
    # Socket per rispondere al server
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    rtt_values = []
    print(f"In attesa di {PACKET_LIMIT} pacchetti UDP per misurazione RTT...")

    while len(rtt_values) < PACKET_LIMIT-1:
        # Ricezione del pacchetto
        raw_data, addr = recv_sock.recvfrom(PACKET_SIZE)
        receive_time = time.time()

        try:
            # Decodifica del payload JSON
            payload = json.loads(raw_data.decode())
            seq = payload.get("seq")
            send_timestamp = payload.get("send_timestamp")

            # Aggiunge il timestamp di ricezione al pacchetto
            payload["receive_timestamp"] = receive_time

            # Invia il pacchetto di ritorno al server
            response_msg = json.dumps(payload).encode()
            send_sock.sendto(response_msg, (addr[0], SERVER_PORT))

            print(f"Pacchetto {seq} ricevuto e rispedito al server")

        except Exception as e:
            print(f"Errore nella gestione del pacchetto: {e}")

    recv_sock.close()
    send_sock.close()

    ip_public = get_public_ip().strip()
    ip_private = get_private_ip().strip()

    # Nota: Il client non calcola direttamente l'RTT, ma potrebbe farlo se necessario
    # In questo caso il server è quello che calcola l'RTT


if __name__ == "__main__":
    rtt_client()