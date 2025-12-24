#!/usr/bin/env python3

import socket
from datetime import datetime

import psycopg2
import requests


def check_database_connection(db_config):
    try:
        conn = psycopg2.connect(**db_config)
        conn.close()
        return True, "Database connection is healthy"
    except Exception as e:
        return False, f"Failed to connect to database: {e}"


def check_network_connectivity(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True, "Network connectivity is healthy"
        else:
            return False, f"Network request failed with status code: {response.status_code}"
    except requests.RequestException as e:
        return False, f"Network request failed: {e}"


def check_service_status(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        if result == 0:
            return True, f"Service at {host}:{port} is healthy"
        else:
            return False, f"Failed to connect to service at {host}:{port}"
    except Exception as e:
        return False, f"Error checking service status: {e}"


def run_health_check():
    db_config = {
        "dbname": "your_dbname",
        "user": "your_user",
        "password": "your_password",
        "host": "your_host",
        "port": "your_port",
    }
    network_url = "http://example.com"
    service_host = "localhost"
    service_port = 8080

    checks = [
        check_database_connection(db_config),
        check_network_connectivity(network_url),
        check_service_status(service_host, service_port),
    ]

    all_passed = True
    for passed, message in checks:
        if not passed:
            all_passed = False
        print(message)

    return all_passed


if __name__ == "__main__":
    start_time = datetime.now()
    print(f"Health check started at {start_time}")
    if run_health_check():
        print("All checks passed. System is ready to start.")
    else:
        print("Some checks failed. System may not be ready to start.")
    end_time = datetime.now()
    print(f"Health check completed at {end_time}")
    print(f"Total time taken: {end_time - start_time}")
