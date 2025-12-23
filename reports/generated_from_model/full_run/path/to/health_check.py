#!/usr/bin/env python3
import requests
import psycopg2
from datetime import datetime
def check_database_connection():
    try:
        conn = psycopg2.connect(
            dbname='your_dbname',
            user='your_user',
            password='your_password',
            host='your_host'
        )
        print('Database connection successful.')
        conn.close()
    except Exception as e:
        print(f'Database connection failed: {e}')
def check_network_connection():
    try:
        response = requests.get('https://www.google.com', timeout=5)
        if response.status_code == 200:
            print('Network connection successful.')
        else:
            print(f'Network connection failed with status code: {response.status_code}')
    except Exception as e:
        print(f'Network connection failed: {e}')
def check_service_status(service_url):
    try:
        response = requests.get(service_url, timeout=5)
        if response.status_code == 200:
            print(f'Service at {service_url} is up.')
        else:
            print(f'Service at {service_url} is down with status code: {response.status_code}')
    except Exception as e:
        print(f'Failed to check service at {service_url}: {e}')
def main():
    start_time = datetime.now()
    print('Starting health check...')
    check_database_connection()
    check_network_connection()
    # Add more services to check here
    # Example: check_service_status('http://your-service-url.com')
    end_time = datetime.now()
    print(f'Health check completed in {end_time - start_time} seconds.')
if __name__ == '__main__':
    main()