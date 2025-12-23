# secure_token_storage.py

import os
import keyring
from cryptography.fernet import Fernet

# Function to generate a new encryption key and save it securely
def generate_key():
    key = Fernet.generate_key()
    # Save the key in the OS keyring with a specific service name
    keyring.set_password('secure_token_storage', 'encryption_key', key.decode())
    return key

# Function to load the encryption key from the OS keyring or generate a new one if not found
def load_key():
    # Try to retrieve the key from the OS keyring
    key = keyring.get_password('secure_token_storage', 'encryption_key')
    if key is None:
        # If the key is not found, generate a new one and save it
        key = generate_key()
    return Fernet(key.encode())

# Function to encrypt and store an API token securely
def store_token(token):
    fernet = load_key()
    encrypted_token = fernet.encrypt(token.encode())
    # Save the encrypted token in a file (e.g., 'token.enc')
    with open('token.enc', 'wb') as file:
        file.write(encrypted_token)

# Function to retrieve and decrypt an API token securely
def get_token():
    fernet = load_key()
    # Read the encrypted token from the file (e.g., 'token.enc')
    with open('token.enc', 'rb') as file:
        encrypted_token = file.read()
    decrypted_token = fernet.decrypt(encrypted_token).decode()
    return decrypted_token

# Example usage
if __name__ == '__main__':
    api_token = 'your_api_token_here'
    store_token(api_token)
    retrieved_token = get_token()
    print('Retrieved Token:', retrieved_token)