import socket
import struct
import threading
import time

if not hasattr(socket, 'SO_TIMESTAMP'):
    socket.SO_TIMESTAMP = 29

UDP_PORT = 5062
TCP_PORT = 5063
SYNC_PORT = 5061

def udp_listener(timestamps, stop_event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMP, 1)
    sock.bind(("0.0.0.0", UDP_PORT))

    print(f"[UDP] In ascolto su porta {UDP_PORT} con SO_TIMESTAMP...")

    while not stop_event.is_set():
        try:
            data, ancdata, _, _ = sock.recvmsg(1024, 1024)
            for cmsg_level, cmsg_type, cmsg_data in ancdata:
                if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMP:
                    tv_sec, tv_usec = struct.unpack("ll", cmsg_data)
                    ts = tv_sec + tv_usec / 1_000_000
                    timestamps.append(ts)
                    print(f"[UDP] Timestamp kernel: {ts}")
        except Exception as e:
            print(f"[UDP] Errore: {e}")
            break
    sock.close()

def handle_tcp_server(timestamps):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", TCP_PORT))
    server_socket.listen()
    print(f"[TCP] In ascolto su porta {TCP_PORT} per invio timestamp...")

    while True:
        conn, addr = server_socket.accept()
        with conn:
            print(f"[TCP] Connessione da {addr}")
            try:
                command = conn.recv(1024).decode()
                if command == "get_timestamps":
                    payload = ",".join(map(str, timestamps)).encode()
                    conn.sendall(payload)
                    print(f"[TCP] Inviati {len(timestamps)} timestamp al client")
            except Exception as e:
                print(f"[TCP] Errore: {e}")

def handle_clock_sync_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", SYNC_PORT))
    server_socket.listen()
    print(f"[SYNC] In ascolto per sincronizzazione clock sulla porta {SYNC_PORT}...")

    while True:
        conn, addr = server_socket.accept()
        with conn:
            print(f"[SYNC] Connessione da {addr}")
            try:
                T_client = conn.recv(1024)
                if not T_client:
                    continue
                T_server = time.time()
                conn.sendall(str(T_server).encode())
                print(f"[SYNC] Risposto con T_server = {T_server}")
            except Exception as e:
                print(f"[SYNC] Errore nella sincronizzazione: {e}")

if __name__ == "__main__":
    print("[SERVER] Avvio server permanente...")

    timestamps = []
    stop_event = threading.Event()

    # Thread dedicato UDP
    udp_thread = threading.Thread(target=udp_listener, args=(timestamps, stop_event), daemon=True)
    udp_thread.start()

    # Thread TCP per invio timestamp
    tcp_thread = threading.Thread(target=handle_tcp_server, args=(timestamps,), daemon=True)
    tcp_thread.start()

    # Thread per clock sync
    sync_thread = threading.Thread(target=handle_clock_sync_server, daemon=True)
    sync_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[SERVER] Terminazione richiesta.")
        stop_event.set()
