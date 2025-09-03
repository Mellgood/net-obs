import socket
import time
import threading
from time import sleep
import struct

CLIENT_IP = "client"
CLIENT_PORT = 5000
PACKET_INTERVAL = 1
NUM_PACKETS = 10
SYNC_PORT = 5053  # Porta per sincronizzazione clock

def udp_sender():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x10)  # Prioritize latency
        for i in range(NUM_PACKETS):
            timestamp = time.time()
            # Usiamo struct per imballare i dati in modo efficiente
            # Formato: 'I' (unsigned int) per seq, 'd' (double) per timestamp
            packet_data = struct.pack('Id', i+1, timestamp)
            sock.sendto(packet_data, (CLIENT_IP, CLIENT_PORT))

            print(f"Inviato pacchetto {i + 1} al client.")
            print(timestamp)
            #time.sleep(PACKET_INTERVAL)

def time_sync_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle
        s.bind(("0.0.0.0", SYNC_PORT))
        s.listen(1)
        print("[ClockSync] In ascolto su porta 5053 per sincronizzazione clock...")
        while True:
            conn, addr = s.accept()
            with conn:
                now = time.time()
                conn.sendall(struct.pack('d', now))  # Invia solo il timestamp
                print(f"[ClockSync] Richiesta sincronizzazione da {addr}, timestamp inviato: {now}")

if __name__ == "__main__":
    threading.Thread(target=time_sync_server, daemon=True).start()
    print("Avvio del server UDP...")
    sleep(3)
    udp_sender()
    print("Trasmissione completata.")