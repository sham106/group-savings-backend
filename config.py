import os
from datetime import timedelta
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Secret key for JWT and general security
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")  
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # TinyPesa Settings
    TINYPESA_API_KEY = os.environ.get('TINYPESA_API_KEY', '')
    TINYPESA_API_SECRET = os.environ.get('TINYPESA_API_SECRET', '')