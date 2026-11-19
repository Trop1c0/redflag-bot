from __future__ import annotations

import secrets
import sqlite3
import time

from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id        INTEGER PRIMARY KEY,
        username       TEXT,
        full_name      TEXT,
        ref_code       TEXT UNIQUE,
        invited_by     TEXT,
        last_admin_id  INTEGER,
        created_at     INTEGER
    );
    CREATE TABLE IF NOT EXISTS applications (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        nickname        TEXT,
        age             INTEGER,
        experience      TEXT,
        equipment       TEXT,
        hours           TEXT,
        source          TEXT,
        ref_code        TEXT,
        status          TEXT DEFAULT 'pending',   -- pending / approved / rejected
        channel_msg_id  INTEGER,
        reviewer_id     INTEGER,
        created_at      INTEGER
    );
    """
)
conn.commit()


def _new_ref_code() -> str:
    while True:
        code = "RF-" + secrets.token_hex(4).upper()
        if not conn.execute("SELECT 1 FROM users WHERE ref_code=?", (code,)).fetchone():
            return code


def get_or_create_user(user_id: int, username: str | None, full_name: str, invited_by: str | None = None):
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if row:
        conn.execute("UPDATE users SET username=?, full_name=? WHERE user_id=?", (username, full_name, user_id))
        conn.commit()
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    # нельзя пригласить самого себя / несуществующий код
    if invited_by and not conn.execute("SELECT 1 FROM users WHERE ref_code=?", (invited_by,)).fetchone():
        invited_by = None
    conn.execute(
        "INSERT INTO users (user_id, username, full_name, ref_code, invited_by, created_at) VALUES (?,?,?,?,?,?)",
        (user_id, username, full_name, _new_ref_code(), invited_by, int(time.time())),
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def get_user(user_id: int):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def set_last_admin(user_id: int, admin_id: int):
    conn.execute("UPDATE users SET last_admin_id=? WHERE user_id=?", (admin_id, user_id))
    conn.commit()


def last_application(user_id: int):
    return conn.execute(
        "SELECT * FROM applications WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()


def create_application(user_id: int, data: dict, ref_code: str) -> int:
    cur = conn.execute(
        """INSERT INTO applications (user_id, nickname, age, experience, equipment, hours, source, ref_code, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, data["nickname"], data["age"], data["experience"], data["equipment"],
         data["hours"], data["source"], ref_code, int(time.time())),
    )
    conn.commit()
    return cur.lastrowid


def get_application(app_id: int):
    return conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()


def set_channel_msg(app_id: int, msg_id: int):
    conn.execute("UPDATE applications SET channel_msg_id=? WHERE id=?", (msg_id, app_id))
    conn.commit()


def set_status(app_id: int, status: str, reviewer_id: int) -> bool:
    """Меняет статус только если заявка ещё pending. Возвращает True если поменяли."""
    cur = conn.execute(
        "UPDATE applications SET status=?, reviewer_id=? WHERE id=? AND status='pending'",
        (status, reviewer_id, app_id),
    )
    conn.commit()
    return cur.rowcount > 0
