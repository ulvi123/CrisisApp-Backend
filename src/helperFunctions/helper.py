from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from cryptography.fernet import Fernet
from src.models import UserToken


def load_key():
    with open("encryption_key.txt","r") as key_file:
        return key_file.read()
    #how to get the encryption key from .env
    
#Loading the encryption key
encryption_key = load_key()

#Next step here is to initialize the cipher using the key
cipher = Fernet(encryption_key.encode())




def get_current_user(token: str, db: Session = Depends(get_db)):
    try:
        # Decrypting the token (using here the same encryption key I used before)
        decrypted_token = cipher.decrypt(token.encode()).decode()

        # Quering the database to ensure this token matches an existing user
        user = db.query(UserToken).filter(UserToken.encrypted_token == token).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
