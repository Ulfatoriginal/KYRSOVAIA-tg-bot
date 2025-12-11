import sqlite3
import requests
import time

DB_FILE = "users.db"

# --- Инициализация базы ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            client_id TEXT,
            client_secret TEXT,
            access_token TEXT,
            refresh_token TEXT,
            expires_at INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


# --- Работа с пользователями ---
def save_user(chat_id, client_id, client_secret, access_token, refresh_token, expires_at):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO users (chat_id, client_id, client_secret, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chat_id, client_id, client_secret, access_token, refresh_token, int(expires_at)))
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT client_id, client_secret, access_token, refresh_token, expires_at FROM users WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"chat_id": chat_id,
                "client_id": row[0],
                "client_secret": row[1],
                "access_token": row[2],
                "refresh_token": row[3],
                "expires_at": row[4]}
    return None

def delete_user(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()


# --- Strava API ---
def exchange_code_for_tokens(client_id, client_secret, code):
    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code"
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["refresh_token"], data["expires_at"]


def refresh_access_token(user):
    """Обновление токена, если протух"""
    if user["expires_at"] > time.time():
        return user["access_token"]
    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": user["client_id"],
        "client_secret": user["client_secret"],
        "grant_type": "refresh_token",
        "refresh_token": user["refresh_token"]
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    data = r.json()
    save_user(user["chat_id"], user["client_id"], user["client_secret"],
              data["access_token"], data["refresh_token"], data["expires_at"])
    return data["access_token"]


def get_activities(user, limit=50):
    token = refresh_access_token(user)
    url = "https://www.strava.com/api/v3/athlete/activities"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params={"per_page": limit})
    r.raise_for_status()
    return r.json()