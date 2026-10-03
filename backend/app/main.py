from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_payload, release_if_expired
from app.modules.cooldown import project_row, project_rows, rules_projection

app = FastAPI(title="Wishclaim", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

def now(): return datetime.now(timezone.utc)

def setting_int(key: str, default: int) -> int:
    c = connect()
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return int(row["value"] if row else default)

def ttl(): return setting_int("ttl_seconds", 86400)
def cooldown(): return setting_int("cooldown_seconds", 3600)

def sweep(c):
    ts = now()
    cd = cooldown()
    for r in c.execute("SELECT * FROM wishes WHERE status='claimed'"):
        rel = release_if_expired(r["status"], r["expires_at"], ts, cd)
        if rel:
            c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=?, cooldown_until=? WHERE id=?",
                      (rel["status"], None, None, None, rel["cooldown_until"], r["id"]))

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes ORDER BY id DESC")]; c.close()
    return project_rows(rows, now())

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone(); c.close()
    if not r: raise HTTPException(404, "not found")
    return project_row(dict(r), now())

class WishIn(BaseModel):
    title: str
    note: str = ""

@app.post("/api/wishes")
def create_wish(body: WishIn):
    c = connect()
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality) VALUES (?,?,?,?)",
                    (body.title, body.note, "open", "clean"))
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid}

class ClaimIn(BaseModel):
    claimer: str

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"], r["cooldown_until"])
    if not allowed["ok"]:
        c.close(); raise HTTPException(409, allowed["reason"])
    p = lock_payload(body.claimer, now(), ttl())
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=?, cooldown_until=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"], p["cooldown_until"], wid))
    c.commit(); c.close(); return p

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    p = release_payload(now(), cooldown(), status="released")
    c.execute("UPDATE wishes SET status=?, claimer=NULL, claimed_at=NULL, expires_at=NULL, cooldown_until=? WHERE id=?",
              (p["status"], p["cooldown_until"], wid))
    c.commit(); c.close(); return {"ok": True, "status": p["status"], "cooldown_until": p["cooldown_until"]}

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "need_claim")
    # fulfilled wishes never enter cooldown
    c.execute("UPDATE wishes SET status='fulfilled', cooldown_until=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "fulfilled"}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]; c.close()
    return project_rows(rows, now())

@app.get("/api/done")
def done():
    c = connect()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE status='fulfilled'")]; c.close()
    return project_rows(rows, now())

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

@app.get("/api/rules")
def rules():
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        **rules_projection(cooldown()),
    }
