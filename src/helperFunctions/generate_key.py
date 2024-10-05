from cryptography.fernet import Fernet

def generate_key():
    return Fernet.generate_key().decode("utf-8")

# Generate the key and save it to a file
with open("encryption_key.txt", "w") as key_file:
    key = generate_key()
    key_file.write(key)
    print(f"Encryption key generated and saved to encryption_key.txt: {key}")
