import jwt
from datetime import datetime, timedelta
from django.conf import settings  
from django.contrib.sessions.backends.db import SessionStore
from .exceptions import SmoothException
from datetime import datetime, timedelta
from django.conf import settings

# Jwt token
def encode_token(payload):
    """Encodes a payload into a JWT token using expiration from SIMPLE_JWT settings."""
    expiration_timedelta = settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME", timedelta(days=2))
    expiration = datetime.now() + expiration_timedelta
    payload["exp"] = expiration    
    secret_key = settings.SECRET_KEY
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token

def decode_token(token):
    """Decodes a JWT token using the SECRET_KEY from settings."""
    try:
        secret_key = settings.SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise SmoothException("Token has expired.")
    except jwt.InvalidTokenError:
        raise SmoothException("Invalid token.")


# Session
def retrieve_session(session_key):
    session = SessionStore(session_key=session_key)
    if not session.exists(session_key):
        return None

    session_data = session.load()
    return session_data

def create_session(data):
    session = SessionStore()
    for key, value in data.items():
        session[key] = value
    session.create()
    return session.session_key

def delete_session(session_key):
    session = SessionStore(session_key=session_key)
    session.delete()
