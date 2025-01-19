import subprocess
import json
import mysql.connector
import requests
import socket

# Configurazione del database
DB_CONFIG = {
    "host": "database",
    "port": "3306",
    "user": "user",
    "password": "test",
    "database": "network_performance"
}
# IP del server iperf3
SERVER_IP = "iperf3-server"
TCP_PORT = 5021
UDP_PORT = 5022
BANDWIDTH = "100M"  # Banda per i test UDP/TCP
CONNECTIONS = 10  # Numero di connessioni (singola o multipla)

# Funzione per creare le tabelle
def create_tables():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jitter_latency (
            id INT AUTO_INCREMENT PRIMARY KEY,
            jitter_ms FLOAT,
            latency_ms FLOAT,
            public_ip VARCHAR(15),
            private_ip VARCHAR(15),
            timestamp DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tcp_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_speed_mbps FLOAT,
            download_speed_mbps FLOAT,
            connections INT,
            public_ip VARCHAR(15),
            private_ip VARCHAR(15),
            timestamp DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS udp_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_speed_mbps FLOAT,
            download_speed_mbps FLOAT,
            connections INT,
            public_ip VARCHAR(15),
            private_ip VARCHAR(15),
            timestamp DATETIME
        )
    """)

    connection.commit()
    cursor.close()
    connection.close()

# Funzione per eseguire iperf e ottenere risultati di jitter e latenza
def run_jitter_latency():
    command = ["iperf3", "-u", "-c", SERVER_IP, "-p", str(UDP_PORT), "-J", "-b", BANDWIDTH]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"Errore durante iperf3 per jitter e latenza: {result.stderr}")
        return None

    try:
        data = json.loads(result.stdout)
        jitter = data["end"]["sum"]["jitter_ms"]
        latency = data["end"]["sum"]["seconds"] * 1000  # Convertito in millisecondi
        return {"jitter": jitter, "latency": latency}
    except (json.JSONDecodeError, KeyError):
        print("Errore nel parsing dei risultati di jitter e latenza.")
        return None

# Funzione per eseguire iperf e ottenere risultati di TCP o UDP
def run_iperf(test_type):
    results = {}
    for direction in ["upload", "download"]:
        command = ["iperf3", "-J", "-P", str(CONNECTIONS)]  # Output JSON e connessioni multiple
        if test_type == "udp":
            command.append("-u")
        if direction == "upload":
            command += ["-c", SERVER_IP, "-p", str(TCP_PORT if test_type == "tcp" else UDP_PORT), "-b", BANDWIDTH]
        elif direction == "download":
            command += ["-R", "-c", SERVER_IP, "-p", str(TCP_PORT if test_type == "tcp" else UDP_PORT), "-b", BANDWIDTH]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Errore durante iperf3 ({test_type}-{direction}): {result.stderr}")
            return None

        try:
            data = json.loads(result.stdout)
            if test_type == "udp":
                # UDP specific parsing
                results[f"{direction}_speed"] = data["end"]["sum"]["bits_per_second"] / 1e6  # Mbps
            else:
                # TCP specific parsing
                if direction == "upload":
                    results["upload_speed"] = data["end"]["sum_sent"]["bits_per_second"] / 1e6  # Mbps
                elif direction == "download":
                    results["download_speed"] = data["end"]["sum_received"]["bits_per_second"] / 1e6  # Mbps
        except (json.JSONDecodeError, KeyError):
            print(f"Errore nel parsing dei risultati iperf3 ({test_type}-{direction}).")
            return None

    return results

# Funzione per salvare i dati nel database
def save_to_db(cursor, table, data, ip_public, ip_private):
    query = f"""
        INSERT INTO {table} (upload_speed_mbps, download_speed_mbps, connections, public_ip, private_ip, timestamp)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """
    cursor.execute(query, (data["upload_speed"], data["download_speed"], CONNECTIONS, ip_public, ip_private))

def save_jitter_latency(cursor, data, ip_public, ip_private):
    query = """
        INSERT INTO jitter_latency (jitter_ms, latency_ms, public_ip, private_ip, timestamp)
        VALUES (%s, %s, %s, %s, NOW())
    """
    cursor.execute(query, (data["jitter"], data["latency"], ip_public, ip_private))

def get_public_ip():
    try:
        response = requests.get("https://api64.ipify.org?format=json")
        public_ip = response.json()["ip"]
    except Exception:
        public_ip = "Impossibile determinare l'IP pubblico"
    return public_ip

def get_private_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))  # Si connette a un DNS pubblico di Google
            private_ip = s.getsockname()[0]
        except Exception:
            private_ip = "Impossibile determinare l'IP privato"
    return private_ip

# Funzione principale
def log_metrics():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    try:
        print("Verifica IP pubblico e privato...")
        ip_public = get_public_ip()
        ip_public = ip_public.strip()
        ip_private = get_private_ip()
        ip_private = ip_private.strip()
        #print(ip_public)
        #print(ip_private)
        # Misurazione Jitter e Latenza
        print("Misurazione jitter e latenza...")
        jitter_latency_data = run_jitter_latency()
        if jitter_latency_data:
            save_jitter_latency(cursor, jitter_latency_data, ip_public, ip_private)

        # Misurazione TCP
        print("Misurazione TCP...")
        tcp_data = run_iperf("tcp")
        if tcp_data:
            save_to_db(cursor, "tcp_metrics", tcp_data, ip_public, ip_private)

        # Misurazione UDP
        print("Misurazione UDP...")
        udp_data = run_iperf("udp")
        if udp_data:
            save_to_db(cursor, "udp_metrics", udp_data, ip_public, ip_private)

        connection.commit()
        print("Dati salvati correttamente.")
    except Exception as e:
        print(f"Errore durante il salvataggio dei dati: {e}")
    finally:
        cursor.close()
        connection.close()

# Main
if __name__ == "__main__":
    create_tables()
    log_metrics()

