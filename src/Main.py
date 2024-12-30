import subprocess
import json
import mysql.connector

# Configurazione del database
DB_CONFIG = {
    "host": "172.20.0.6",
    "port": "3306",
    "user": "user",
    "password": "test",
    "database": "network_performance"
}
# IP del server iperf3
SERVER_IP = "172.20.0.4" ############### DA MODIFICARE INSERENDO L'INDIRIZZO DEL CONTAINER 'iperf3-server'##########
TCP_PORT = 5021
UDP_PORT = 5022
BANDWIDTH = "100M"  # Banda per i test UDP/TCP

# Funzione per creare le tabelle
def create_tables():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jitter_latency (
            id INT AUTO_INCREMENT PRIMARY KEY,
            jitter_ms FLOAT,
            latency_ms FLOAT,
            timestamp DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tcp_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_speed_mbps FLOAT,
            download_speed_mbps FLOAT,
            timestamp DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS udp_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_speed_mbps FLOAT,
            download_speed_mbps FLOAT,
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
        command = ["iperf3", "-J"]  # Output JSON
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
            if direction == "upload":
                results["upload_speed"] = data["end"]["sum_sent"]["bits_per_second"] / 1e6  # Mbps
            elif direction == "download":
                results["download_speed"] = data["end"]["sum_received"]["bits_per_second"] / 1e6  # Mbps
        except (json.JSONDecodeError, KeyError):
            print(f"Errore nel parsing dei risultati iperf3 ({test_type}-{direction}).")
            return None

    return results

# Funzione per salvare i dati nel database
def save_to_db(cursor, table, data):
    query = f"""
        INSERT INTO {table} (upload_speed_mbps, download_speed_mbps, timestamp)
        VALUES (%s, %s, NOW())
    """
    cursor.execute(query, (data["upload_speed"], data["download_speed"]))

def save_jitter_latency(cursor, data):
    query = """
        INSERT INTO jitter_latency (jitter_ms, latency_ms, timestamp)
        VALUES (%s, %s, NOW())
    """
    cursor.execute(query, (data["jitter"], data["latency"]))

# Funzione principale
def log_metrics():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    try:
        # Misurazione Jitter e Latenza
        print("Misurazione jitter e latenza...")
        jitter_latency_data = run_jitter_latency()
        if jitter_latency_data:
            save_jitter_latency(cursor, jitter_latency_data)

        # Misurazione TCP
        print("Misurazione TCP...")
        tcp_data = run_iperf("tcp")
        if tcp_data:
            save_to_db(cursor, "tcp_metrics", tcp_data)

        # Misurazione UDP
        print("Misurazione UDP...")
        udp_data = run_iperf("udp")
        if udp_data:
            save_to_db(cursor, "udp_metrics", udp_data)

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
