from cryptography.fernet import Fernet


def load_key():
    with open("encryption_key.txt","r") as key_file:
        return key_file.read()
    #how to get the encryption key from .env
    
#Loading the encryption key
encryption_key = load_key()

#Next step here is to initialize the cipher using the key
cipher = Fernet(encryption_key.encode())