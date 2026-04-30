from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import time

app = FastAPI()
DB = "license.db"


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


# ===== MODEL =====
class VerifyRequest(BaseModel):
    key: str
    hwid: str


# ===== VERIFY API =====
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
