import os
import mysql.connector
import pymysql
import asyncio
import aiomysql
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()  # ✅ Define app first

# ✅ Mount static directory to serve files (thumbnails, uploads, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

    # Secure session cookies in production
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SONGS_FOLDER = os.path.join(BASE_DIR, 'static', 'songs')

    # Allowed CORS origins
    CORS_ALLOWED_ORIGINS = [
        "http://example.com",
        "http://192.168.100.2:5000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:8080",
        "http://192.168.100.2:8080"
    ]

    FRONTEND_SERVER = "http://localhost:8080"
    BACKEND_SERVER = "http://192.168.100.2:5000"  # ✅ Fixed extra space

    thumbnailPath = f"{BACKEND_SERVER}/static/thumbnails"
    profilePath = f"{BACKEND_SERVER}/static/uploads"

    mydb = pymysql.connect(
        host="localhost",
        user="root",
        password="0000",
        database="injustify"
    )

    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "0000"),
        "db": os.getenv("DB_NAME", "injustify"),
        "port": 3306
    }

    pool = None  # ✅ Persistent connection pool

    @staticmethod
    async def init_db_pool():
        """ Initialize and store the connection pool. Should be called once at startup. """
        if Config.pool is None:
            Config.pool = await aiomysql.create_pool(**Config.db_config)
    
    @staticmethod
    async def get_db_connection():
        """ Get a database connection from the pool. """
        if Config.pool is None:
            await Config.init_db_pool()  # Ensure the pool is initialized
        
        conn = await Config.pool.acquire()  # ✅ Get connection
        return conn

    @staticmethod
    async def close_db_pool():
        """ Close the database connection pool. Should be called at shutdown. """
        if Config.pool:
            Config.pool.close()
            await Config.pool.wait_closed()
