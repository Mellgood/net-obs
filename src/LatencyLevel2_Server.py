import socket
from time import sleep
import pyshark
import threading
import time

# Porte fisse per AWS
UDP_PORT = 5052
TCP_PORT = 5053
SYNC_PORT = 5051
INTERFACE = "eth0"
TOS = 0x10

server_timestamps = []
timestamps_lock = threading.Lock()

def receive_packets():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", UDP_PORT))
    print(f"[UDP] In ascolto su {UDP_PORT}...")
    while True:
        data, addr = udp_sock.recvfrom(1024)
        print(f"[UDP] Ricevuto pacchetto da {addr}")

def sniff_packets():
    print(f"[Sniffer] Sniffing su {INTERFACE} DSCP {TOS}...")
    capture = pyshark.LiveCapture(
        interface=INTERFACE,
        display_filter=f"ip.dsfield.dscp == 4 and udp.port == {UDP_PORT}",
        use_json=True
    )
    for packet in capture.sniff_continuously():
        try:
            if hasattr(packet, 'ip'):
                ts = float(packet.sniff_timestamp)
                with timestamps_lock:
                    server_timestamps.append(ts)
                print(f"[Sniffer] Registrato: {ts}")
        except AttributeError:
            continue

def send_timestamps_to_client():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind(("0.0.0.0", TCP_PORT))
    tcp_sock.listen(5)
    print(f"[TCP] In ascolto su {TCP_PORT}...")

    while True:
        conn, addr = tcp_sock.accept()
        with conn:
            with timestamps_lock:
                if server_timestamps:
                    payload = ",".join(map(str, server_timestamps)).encode()
                    conn.sendall(payload)
                    print(f"[TCP] Inviati {len(server_timestamps)} timestamp a {addr}")
                    server_timestamps.clear()
                else:
                    conn.sendall(b"No timestamps available")
                    print(f"[TCP] Nessun timestamp per {addr}")

def serve_clock_sync():
    sync_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sync_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sync_sock.bind(("0.0.0.0", SYNC_PORT))
    sync_sock.listen(5)
    print(f"[ClockSync] In ascolto su {SYNC_PORT}...")

    while True:
        conn, addr = sync_sock.accept()
        with conn:
            current_time = str(time.time())
            conn.sendall(current_time.encode())
            print(f"[ClockSync] Inviato tempo: {current_time} a {addr}")

if __name__ == "__main__":
    print("[Server] Avvio server persistente su AWS")

    threading.Thread(target=receive_packets, daemon=True).start()
    threading.Thread(target=sniff_packets, daemon=True).start()
    threading.Thread(target=send_timestamps_to_client, daemon=True).start()
    threading.Thread(target=serve_clock_sync, daemon=True).start()

    while True:
        time.sleep(10)  # Mantiene attivo il main thread

