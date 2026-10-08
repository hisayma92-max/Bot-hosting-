import sqlite3
from pathlib import Path

class Database:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def init(self):
        with self.conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                status TEXT NOT NULL DEFAULT 'Free User',
                package TEXT NOT NULL DEFAULT 'Free',
                file_limit INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS upgrade_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                package TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

    def upsert_user(self, user_id, username, first_name, last_name, status="Free User"):
        with self.conn() as c:
            c.execute("""
            INSERT INTO users(user_id, username, first_name, last_name, status)
            VALUES(?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
              username=excluded.username,
              first_name=excluded.first_name,
              last_name=excluded.last_name,
              updated_at=CURRENT_TIMESTAMP
            """, (user_id, username, first_name, last_name, status))

    def get_user(self, user_id):
        with self.conn() as c:
            row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return row
        self.upsert_user(user_id, "", "", "")
        with self.conn() as c:
            return c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

    def file_count(self, user_id):
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM files WHERE user_id=?", (user_id,)).fetchone()[0]

    def add_file(self, user_id, filename, slug, path):
        with self.conn() as c:
            c.execute("INSERT INTO files(user_id,filename,slug,path) VALUES(?,?,?,?)",
                      (user_id, filename, slug, path))

    def list_files(self, user_id):
        with self.conn() as c:
            return c.execute("SELECT * FROM files WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()

    def user_count(self):
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def total_files(self):
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    def all_user_ids(self):
        with self.conn() as c:
            return [r[0] for r in c.execute("SELECT user_id FROM users ORDER BY user_id")]

    def latest_users(self, limit=10):
        with self.conn() as c:
            return c.execute("SELECT * FROM users ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()

    def add_upgrade_request(self, user_id, package):
        with self.conn() as c:
            cur = c.execute("INSERT INTO upgrade_requests(user_id,package) VALUES(?,?)", (user_id, package))
            return cur.lastrowid

    def pending_upgrades(self, limit=20):
        with self.conn() as c:
            return c.execute("""
                SELECT r.*, u.username, u.first_name
                FROM upgrade_requests r LEFT JOIN users u ON u.user_id=r.user_id
                WHERE r.status='pending' ORDER BY r.id DESC LIMIT ?
            """, (limit,)).fetchall()

    def set_upgrade_status(self, request_id, status):
        with self.conn() as c:
            c.execute("UPDATE upgrade_requests SET status=? WHERE id=?", (status, request_id))

    def set_package(self, user_id, package, status, file_limit):
        with self.conn() as c:
            c.execute("""UPDATE users SET package=?, status=?, file_limit=?, updated_at=CURRENT_TIMESTAMP
                         WHERE user_id=?""", (package, status, file_limit, user_id))

    def get_setting(self, key, default=""):
        with self.conn() as c:
            r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return r[0] if r else default

    def set_setting(self, key, value):
        with self.conn() as c:
            c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (key, value))
