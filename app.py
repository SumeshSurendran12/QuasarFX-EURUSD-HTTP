import os, time
from fastapi import FastAPI
from pydantic import BaseModel
from eurusd_api import EURUSDAPI, APIError

app = FastAPI(title="QuasarFX EURUSD Bot", version="1.0.0")

class Status(BaseModel):
    ok: bool
    ts: float
    message: str | None = None
    price: float | None = None
    balance: float | None = None
    equity: float | None = None

def client_from_env()->EURUSDAPI:
    user = os.getenv("USERNAME","")
    pwd  = os.getenv("PASSWORD","")
    appkey = os.getenv("APP_KEY","")
    return EURUSDAPI(user, pwd, appkey)

@app.get("/healthz", response_model=Status)
def healthz():
    return Status(ok=True, ts=time.time(), message="healthy")

@app.get("/readyz", response_model=Status)
def readyz():
    """Readiness probe: verifies we can reach upstreams (login + price)."""
    api = client_from_env()
    try:
        api.login()
        price = api.get_price()
        return Status(ok=True, ts=time.time(), message="ready", price=price)
    except Exception as e:
        return Status(ok=False, ts=time.time(), message=str(e))
    finally:
        try:
            api.logout()
        except Exception:
            pass

@app.get("/status", response_model=Status)
def status(live: bool = True):
    api = client_from_env()
    try:
        if live:
            api.login()
        price = api.get_price()
        balance = equity = None
        if live:
            try:
                bal = api.get_balance()
                balance = float(bal.get("Balance") or 0) if bal else None
                equity  = float(bal.get("Equity") or 0) if bal else None
            except Exception:
                pass
        return Status(ok=True, ts=time.time(), price=price, balance=balance, equity=equity)
    except Exception as e:
        return Status(ok=False, ts=time.time(), message=str(e))
    finally:
        try:
            if live:
                api.logout()
        except Exception:
            pass