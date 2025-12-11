import sqlite3
import time

DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # создаём таблицу, если её нет
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        client_id TEXT,
        client_secret TEXT,
        refresh_token TEXT,
        access_token TEXT,
        token_expires_at REAL
    )
    """)
    conn.commit()
    conn.close()

def save_user(chat_id, client_id, client_secret, refresh_token, access_token, expires_at):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO users (chat_id, client_id, client_secret, refresh_token, access_token, token_expires_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (chat_id, client_id, client_secret, refresh_token, access_token, expires_at))
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    SELECT client_id, client_secret, refresh_token, access_token, token_expires_at
    FROM users WHERE chat_id=?
    """, (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "client_id": row[0],
            "client_secret": row[1],
            "refresh_token": row[2],
            "access_token": row[3],
            "token_expires_at": row[4]
        }
    return None

def delete_user(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()
