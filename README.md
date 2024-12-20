# agcom-net-obs

This project sets up two Ubuntu containers connected to a custom Docker network (`myDockerNet`). Each container has the necessary tools for network testing and diagnostics, including:

- `iperf3` for network performance testing
- `ping`, `dnsutils`, and `curl` for connectivity testing
- `ip`, `route`, and `ifconfig` for network configuration management

---

## Prerequisites

Make sure you have the following installed on your system:

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: [Install Docker Compose](https://docs.docker.com/compose/install/)

---

## Run

```bash
docker compose up --build --force-recreate
```