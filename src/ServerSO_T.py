import socket
import struct
import threading
import time

if not hasattr(socket, 'SO_TIMESTAMP'):
    socket.SO_TIMESTAMP = 29

UDP_PORT = 5062
TCP_PORT = 5063
SYNC_PORT = 5061
MAX_PACKETS = 2

def receive_udp_packets(timestamps):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMP, 1)
    sock.bind(("0.0.0.0", UDP_PORT))

    print(f"[UDP] In ascolto su porta {UDP_PORT} con SO_TIMESTAMP...")

    while len(timestamps) < MAX_PACKETS:
        data, ancdata, _, _ = sock.recvmsg(1024, 1024)
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMP:
                                            #This socket option enables timestamping of datagrams on the reception
                                            #path. Because the destination socket, if any, is not known early in
                                            #the network stack, the feature has to be enabled for all packets. The
                                            #same is true for all early receive timestamp options.
                tv_sec, tv_usec = struct.unpack("ll", cmsg_data)
                ts = tv_sec + tv_usec / 1_000_000
                timestamps.append(ts)
                print(f"[UDP] Timestamp kernel: {ts}")
    sock.close()

def handle_tcp_send(timestamps):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", TCP_PORT))
        s.listen(1)
        print(f"[TCP] In ascolto su porta {TCP_PORT} per invio timestamp...")
        conn, _ = s.accept()
        with conn:
            time.sleep(1)
            payload = ",".join(map(str, timestamps)).encode()
            conn.sendall(payload)
            print(f"[TCP] Inviati {len(timestamps)} timestamp al client")

def handle_clock_sync():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", SYNC_PORT))
        s.listen(1)
        print("[SYNC] In ascolto per sincronizzazione clock sulla porta 5051...")
        conn, addr = s.accept()
        with conn:
            print(f"[SYNC] Connessione da {addr}")
            try:
                T_client = conn.recv(1024)
                if not T_client:
                    print("[SYNC] Nessun dato ricevuto dal client.")
                    return
                T_server = time.time()
                conn.sendall(str(T_server).encode())
                print(f"[SYNC] Risposto con T_server = {T_server}")
            except Exception as e:
                print(f"[SYNC] Errore nella sincronizzazione: {e}")

if __name__ == "__main__":
    print("[SERVER] Avvio server in modalità continua...")
    while True:
        # Nuova sincronizzazione e ciclo completo per ogni richiesta
        timestamps = []  # Reinizializza i timestamp

        handle_clock_sync()

        # Avvia il thread UDP per la raccolta dei timestamp
        udp_thread = threading.Thread(target=receive_udp_packets, args=(timestamps,))
        udp_thread.start()

        # Invio dei timestamp via TCP
        handle_tcp_send(timestamps)

        udp_thread.join()
        print("[SERVER] Ciclo completato. In attesa di una nuova richiesta...\n")
