from cryptography.fernet import Fernet
from app.core.config import settings

def _cipher():
    if not settings.token_encryption_key:
        raise RuntimeError('TOKEN_ENCRYPTION_KEY não configurada')
    return Fernet(settings.token_encryption_key.encode())

def encrypt(value:str)->str:
    return _cipher().encrypt(value.encode()).decode() if value else ''

def decrypt(value:str)->str:
    return _cipher().decrypt(value.encode()).decode() if value else ''
