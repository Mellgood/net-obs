import socket
from time import sleep
import pyshark
import threading
import time

# Configurazione costanti
UDP_PORT = 5052
TCP_PORT = 5053
SYNC_PORT = 5051
INTERFACE = "eth0"
TOS = 0x10


def receive_packets(stop_event):
    """Riceve pacchetti UDP"""
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", UDP_PORT))
    udp_sock.settimeout(1.0)
    print(f"[UDP] In ascolto su porta {UDP_PORT}...")
    try:
        while not stop_event.is_set():
            try:
                data, addr = udp_sock.recvfrom(1024)
                print(f"[UDP] Ricevuto pacchetto da {addr}")
            except socket.timeout:
                continue
    finally:
        udp_sock.close()
        print("[UDP] Socket chiuso.")


def sniff_packets(stop_event, timestamps):
    """Cattura pacchetti UDP con DSCP corretto"""
    print(f"[Sniffer] Sniffing su interfaccia {INTERFACE} con DSCP {TOS}...")
    capture = None
    try:
        capture = pyshark.LiveCapture(
            interface=INTERFACE,
            display_filter=f"ip.dsfield.dscp == 4 and udp.port == {UDP_PORT}",
            use_json=True
        )

        for packet in capture.sniff_continuously():
            if stop_event.is_set():
                break
            try:
                if hasattr(packet, 'ip'):
                    ts = float(packet.sniff_timestamp)
                    timestamps.append(ts)
                    print(f"[Sniffer] Registrato timestamp: {ts}")
            except AttributeError:
                continue
    except Exception as e:
        print(f"[Sniffer] Errore critico: {str(e)}")
    finally:
        if capture:
            capture.close()
            print("[Sniffer] Cattura terminata.")


def send_timestamps_to_client(timestamps, stop_event):
    """Invia i timestamp via TCP"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", TCP_PORT))
        s.listen(1)
        s.settimeout(1.0)

        print(f"[TCP] In ascolto su porta {TCP_PORT}...")
        while not stop_event.is_set():
            try:
                conn, addr = s.accept()
                print(f"[TCP] Connessione accettata da {addr}")

                if timestamps:
                    payload = ",".join(map(str, timestamps)).encode()
                    conn.sendall(payload)
                    print(f"[TCP] Inviati {len(timestamps)} timestamp")
                else:
                    conn.sendall(b"No timestamps available")
                    print("[TCP] Nessun timestamp disponibile")

                conn.close()
                stop_event.set()
                break
            except socket.timeout:
                continue


def serve_clock_sync():
    """Sincronizzazione orologio server"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", SYNC_PORT))
        s.listen(1)
        s.settimeout(10)
        print(f"[ClockSync] In ascolto sulla porta {SYNC_PORT}...")
        try:
            conn, addr = s.accept()
            with conn:
                current_time = str(time.time())
                conn.sendall(current_time.encode())
                print(f"[ClockSync] Inviato tempo: {current_time} a {addr}")
        except socket.timeout:
            print("[ClockSync] Timeout: nessuna richiesta ricevuta.")


def run_server_cycle():
    """Esegue un ciclo completo di ascolto e risposta"""
    stop_event = threading.Event()
    server_timestamps = []

    print("\n[Server] Nuovo ciclo avviato...")

    # 1. Sincronizzazione orologio
    serve_clock_sync()

    # 2. Avvia thread per sniffing e ricezione
    sniff_thread = threading.Thread(target=sniff_packets, args=(stop_event, server_timestamps))
    receive_thread = threading.Thread(target=receive_packets, args=(stop_event,))
    send_thread = threading.Thread(target=send_timestamps_to_client, args=(server_timestamps, stop_event))

    sniff_thread.start()
    receive_thread.start()
    sleep(5)  # Attendi avvio ricezione/sniffing
    send_thread.start()

    send_thread.join()

    stop_event.set()
    sniff_thread.join(timeout=2)
    receive_thread.join(timeout=2)
    print("[Server] Ciclo completato.")


if __name__ == "__main__":
    try:
        CLIENT_IP = socket.gethostbyname('client')
        SERVER_IP = socket.gethostbyname('server')
        print(f"Configurazione avviata - Server: {SERVER_IP}, Client: {CLIENT_IP}")
        while True:
            run_server_cycle()
            print("[Main] In attesa di nuova richiesta...\n")
            sleep(2)
    except KeyboardInterrupt:
        print("\n[Main] Interruzione manuale, chiusura server.")
