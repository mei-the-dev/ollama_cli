import os
import base64
from cryptography.fernet import Fernet
try:
    from keyring import set_password, get_password
except ImportError:
    keyring = None

def generate_key():
    return Fernet.generate_key()

def encrypt_token(token, key):
    fernet = Fernet(key)
    encrypted_token = fernet.encrypt(token.encode())
    return encrypted_token.decode()

def decrypt_token(encrypted_token, key):
    fernet = Fernet(key)
    decrypted_token = fernet.decrypt(encrypted_token.encode()).decode()
    return decrypted_token

def store_token(service_name, token, key=None):
    if keyring is not None:
        set_password(service_name, 'api_token', token)
    else:
        encrypted_token = encrypt_token(token, key)
        with open(f'{service_name}_token.enc', 'w') as f:
            f.write(encrypted_token)

def retrieve_token(service_name, key=None):
    if keyring is not None:
        token = get_password(service_name, 'api_token')
        return token
    else:
        with open(f'{service_name}_token.enc', 'r') as f:
            encrypted_token = f.read()
        decrypted_token = decrypt_token(encrypted_token, key)
        return decrypted_token