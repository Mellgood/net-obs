import socket
import time
import json
from datetime import datetime

# Configurazione
CLIENT_IP = "client"  # Sostituisci con l'IP del client
CLIENT_PORT = 5000  # Porta su cui il client è in ascolto
PACKET_INTERVAL = 1  # Intervallo tra pacchetti in secondi
NUM_PACKETS = 10  # Numero di pacchetti da inviare

def get_timezone_offset():
    """Restituisce il fuso orario locale in secondi."""
    local_tz = datetime.now().astimezone().tzinfo
    return int(local_tz.utcoffset(None).total_seconds())

def send_udp_packets():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for i in range(NUM_PACKETS):
            timestamp = time.time()  # Timestamp in secondi con decimali
            timezone_offset = get_timezone_offset()
            # Creazione del pacchetto
            packet_data = {
                "seq": i + 1,
                "timestamp": timestamp,
                "timezone_offset": timezone_offset
            }
            # Conversione in JSON
            message = json.dumps(packet_data).encode()
            # Invio del pacchetto
            sock.sendto(message, (CLIENT_IP, CLIENT_PORT))
            print(f"Inviato pacchetto {i + 1} al client.")
            time.sleep(PACKET_INTERVAL)

if __name__ == "__main__":
    print("Avvio del server UDP...")
    send_udp_packets()
    print("Trasmissione completata.")


