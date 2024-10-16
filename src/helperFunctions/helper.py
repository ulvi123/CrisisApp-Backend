import logging
from cryptography.fernet import Fernet
from fastapi import Cookie, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from src.database import get_db
from cryptography.fernet import Fernet
from src.models import UserToken


# def load_key():
#     with open("encryption_key.txt","r") as key_file:
#         return key_file.read()
#     #how to get the encryption key from .env
 
# #Loading the encryption key
# encryption_key = load_key()

#Next step here is to initialize the cipher using the key
# cipher = Fernet(encryption_key.encode())


#This function is aimed to protect the routes based on the user role assigned to the token
def get_current_user(token: str=Cookie(None),authorization: str = Header(None), db: Session = Depends(get_db)):
    
    #First action is to identify the token source
    if not token and authorization:
        if authorization.startswith("Bearer "):	
            token = authorization.split(" ")[1]
    
    if not token:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail =f"Invalid or expired token",	
            headers={"WWW-Authenticate": "Bearer"},
        )
    #Second action is to decrypt the token
    logging.info(f"Received token before decryption: {token}")

    try:
        decrypted_token = cipher.decrypt(token.encode()).decode() # type: ignore
    except Exception as e:
        logging.error(f"Error decrypting token: {str(e)}")
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail =f"Invalid or expired token",	
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Querying the database to ensure this token matches an existing user
    user = db.query(UserToken).filter(UserToken.user_id == decrypted_token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

