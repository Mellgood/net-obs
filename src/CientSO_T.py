import socket
import time
import numpy as np

SERVER = socket.gethostbyname("server")
UDP_PORT = 5062
TCP_PORT = 5063
COUNT = 3

client_timestamps = []
server_timestamps = []

def sync_clock1():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER, TCP_PORT))
        T1 = time.time()
        s.sendall(b"sync")
        T_server_bytes = s.recv(1024)
        T4 = time.time()
        T_server = float(T_server_bytes.decode())
        offset = T_server - ((T1 + T4) / 2)
        print(f"[SYNC] Offset stimato: {offset:.6f} s")
        return offset
def sync_clock():
    """Esegue la sincronizzazione del clock con il server."""
    SYNC_PORT = 5061
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER, SYNC_PORT))
        T1 = time.time()
        s.sendall(str(T1).encode())
        T_server_bytes = s.recv(1024)
        T2 = time.time()
        T_server = float(T_server_bytes.decode())
        offset = T_server - ((T1 + T2) / 2)
        print(f"[SYNC] Offset calcolato: {offset:.6f} sec")
        return offset

def send_udp_packets():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(COUNT):
        msg = f"PKT_{i}".encode()
        sock.sendto(msg, (SERVER, UDP_PORT))
        ts = time.time()
        client_timestamps.append(ts)
        print(f"[UDP] Inviato PKT_{i} alle {ts}")
        time.sleep(0.05)
    sock.close()

def receive_server_timestamps():
    global server_timestamps
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER, TCP_PORT))
        s.sendall(b"get_timestamps")
        data = s.recv(4096).decode()
        server_timestamps = list(map(float, data.split(',')))

def compute_latency(offset):
    adjusted_server_ts = [ts - offset for ts in server_timestamps]
    print(adjusted_server_ts)
    print(client_timestamps[:len(adjusted_server_ts)])
    #latencies =  np.array(adjusted_server_ts) - np.array(client_timestamps[1:len(adjusted_server_ts)])
    #latencies =  np.array(client_timestamps) - np.array(adjusted_server_ts[-len(client_timestamps):])
    min_len = min(len(client_timestamps), len(adjusted_server_ts))
    client_last = client_timestamps[-min_len:]
    server_last = adjusted_server_ts[-min_len:]
    latencies = np.array(client_last) - np.array(server_last)
    print(f"[RISULTATI]")
    for i, l in enumerate(latencies):
        print(f"Pacchetto {i}: {l*1000:.3f} ms")
    print(f"Latenza media: {np.mean(latencies)*1000:.3f} ms")
    print(f"Jitter: {np.std(latencies)*1000:.3f} ms")

if __name__ == "__main__":
    print("[STEP] Sincronizzazione clock...")
    time.sleep(2)
    offset = sync_clock()

    print("[STEP] Invio pacchetti UDP...")
    send_udp_packets()

    print("[STEP] Attesa e ricezione timestamp dal server...")
    time.sleep(2)
    receive_server_timestamps()

    print("[STEP] Calcolo latenza...")
    compute_latency(offset)
