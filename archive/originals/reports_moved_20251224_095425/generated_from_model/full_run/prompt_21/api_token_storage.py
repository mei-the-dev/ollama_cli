#!/usr/bin/env python3
import os

import keyring
from cryptography.fernet import Fernet


def store_api_token(token, service_name="api_token", username="default_user"):
    # Try to use the OS keyring first
    try:
        keyring.set_password(service_name, username, token)
        print("API token stored in the OS keyring.")
    except Exception as e:
        print(f"Failed to store API token in keyring: {e}\nFalling back to file encryption.")
        # Generate a key for encryption if it doesn't exist
        key_path = os.path.expanduser("~/.api_token_key")
        if not os.path.exists(key_path):
            key = Fernet.generate_key()
            with open(key_path, "wb") as key_file:
                key_file.write(key)
        else:
            with open(key_path, "rb") as key_file:
                key = key_file.read()
        # Encrypt the token
        cipher_suite = Fernet(key)
        encrypted_token = cipher_suite.encrypt(token.encode())
        # Store the encrypted token in a file
        token_path = os.path.expanduser("~/.api_token")
        with open(token_path, "wb") as token_file:
            token_file.write(encrypted_token)
        print("API token stored in an encrypted file.")


def retrieve_api_token(service_name="api_token", username="default_user"):
    # Try to retrieve the API token from the OS keyring
    try:
        token = keyring.get_password(service_name, username)
        if token is not None:
            print("API token retrieved from the OS keyring.")
            return token
    except Exception as e:
        print(f"Failed to retrieve API token from keyring: {e}\nAttempting to decrypt from file.")
    # If keyring retrieval fails, try to decrypt from a file
    key_path = os.path.expanduser("~/.api_token_key")
    if not os.path.exists(key_path):
        raise Exception("No encryption key found. Cannot retrieve API token.")
    with open(key_path, "rb") as key_file:
        key = key_file.read()
    cipher_suite = Fernet(key)
    token_path = os.path.expanduser("~/.api_token")
    if not os.path.exists(token_path):
        raise Exception("No encrypted API token found.")
    with open(token_path, "rb") as token_file:
        encrypted_token = token_file.read()
    decrypted_token = cipher_suite.decrypt(encrypted_token).decode()
    print("API token retrieved from an encrypted file.")
    return decrypted_token
