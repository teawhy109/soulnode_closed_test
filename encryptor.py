from Crypto.Cipher import AES
import base64
import os

def pad(s):
    pad_len = AES.block_size - len(s.encode('utf-8')) % AES.block_size
    return s + chr(pad_len) * pad_len

def unpad(s):
    return s[:-ord(s[-1])]

def encrypt_file(file_path, key):
    with open(file_path, 'r', encoding='utf-8') as file:
        plaintext = file.read()

    key = key.encode('utf-8')
    key = key[:32].ljust(32, b'\0') # Ensure 32 bytes for AES-256
    iv = os.urandom(16)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(plaintext).encode('utf-8')
    encrypted = cipher.encrypt(padded_data)
    data = base64.b64encode(iv + encrypted)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(data.decode('utf-8'))

def decrypt_file(file_path, key):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = base64.b64decode(file.read())

    iv = data[:16]
    encrypted = data[16:]

    key = key.encode('utf-8')
    key = key[:32].ljust(32, b'\0') # Ensure 32 bytes for AES-256

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted)
    plaintext = unpad(decrypted.decode('utf-8'))

    return plaintext

if __name__ == '__main__':
    file_path = 'mylastday.json'
    key = 'teawhylegacykey2025'
    encrypt_file(file_path, key)
    print(f"{file_path} has been encrypted successfully.")