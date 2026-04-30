from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import time

app = FastAPI()

DB = "license.db"

# ===== ADMIN SECRET (đổi cái này) =====
ADMIN_KEY = "123456"


# ===== INIT DB =====
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            hwid TEXT,
            expiry INTEGER,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# MODELS
# =========================

class VerifyRequest(BaseModel):
    key: str
    hwid: str


class CreateRequest(BaseModel):
    key: str
    hwid: str
    expiry: int
    admin_key: str


class RevokeRequest(BaseModel):
    key: str
    admin_key: str


# =========================
# VERIFY KEY (CLIENT)
# =========================
@app.post("/verify")
def verify(req: VerifyRequest):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT hwid, expiry, status FROM licenses WHERE key=?",
              (req.key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"status": "invalid", "reason": "key not found"}

    hwid, expiry, status = row
    now = int(time.time())

    if status != "active":
        return {"status": "invalid", "reason": "banned"}

    if now > expiry:
        return {"status": "invalid", "reason": "expired"}

    if hwid != req.hwid:
        return {"status": "invalid", "reason": "hwid mismatch"}

    return {"status": "valid"}


# =========================
# CREATE KEY (ADMIN TOOL)
# =========================
@app.post("/create")
def create(req: CreateRequest):

    if req.admin_key != ADMIN_KEY:
        return {"status": "error", "reason": "unauthorized"}

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO licenses (key, hwid, expiry, status)
            VALUES (?, ?, ?, 'active')
        """, (req.key, req.hwid, req.expiry))

        conn.commit()

        return {"status": "created"}

    except Exception as e:
        return {"status": "error", "reason": str(e)}

    finally:
        conn.close()


# =========================
# REVOKE KEY (BAN)
# =========================
@app.post("/revoke")
def revoke(req: RevokeRequest):

    if req.admin_key != ADMIN_KEY:
        return {"status": "error", "reason": "unauthorized"}

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        UPDATE licenses
        SET status='banned'
        WHERE key=?
    """, (req.key,))

    conn.commit()
    conn.close()

    return {"status": "revoked"}
