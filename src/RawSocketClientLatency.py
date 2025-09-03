import socket
import time
import struct
import threading

UDP_PORT = 5000
PACKET_SIZE = 1024
PACKET_LIMIT = 10
SERVER_IP = "server"  # IP/hostname del server per clock sync
SYNC_PORT = 5053


def sync_clock_with_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle
            s.settimeout(1)  # Timeout più breve
            T1 = time.time()
            s.connect((SERVER_IP, SYNC_PORT))
            data = s.recv(8)  # Riceviamo solo 8 byte per il double
            T4 = time.time()
            T_server = struct.unpack('d', data)[0]
            estimated_offset = T_server - ((T1 + T4) / 2)
            print(f"[ClockSync] Offset stimato: {estimated_offset:.6f} s")
            return estimated_offset
    except Exception as e:
        print(f"[ClockSync] Errore: {e}")
        return 0.0


def raw_socket_client():
    offset = sync_clock_with_server()

    # Usiamo SOCK_DGRAM invece di SOCK_RAW per evitare di dover parsare l'header IP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x10)  # Prioritize latency
    sock.bind(("0.0.0.0", UDP_PORT))

    latencies = []
    print(f"In attesa di {PACKET_LIMIT} pacchetti UDP per calcolare latenza e jitter...")

    while len(latencies) < PACKET_LIMIT:
        data, addr = sock.recvfrom(PACKET_SIZE)
        received_time = time.time() - offset
        # Decodifica i dati binari usando struct
        try:
            seq, sent_time = struct.unpack('Id', data)
            latency = (received_time - sent_time) * 1000  # ms
            latencies.append(latency)
            print(f"Pacchetto {seq} ricevuto - Latenza: {latency:.6f} ms")
        except Exception as e:
            print(f"Errore nella decodifica del pacchetto: {e}")

    mean_latency = sum(latencies) / len(latencies)
    print(f"Latenza media: {mean_latency:.6f} ms")


if __name__ == "__main__":
    raw_socket_client()
