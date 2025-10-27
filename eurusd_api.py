from __future__ import annotations
import json, time
from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests

class APIError(Exception): pass

@dataclass
class OrderResult:
    raw: Dict[str, Any]
    order_id: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None

class EURUSDAPI:
    SYMBOL = "EUR/USD"
    PIP = 0.0001
    PRECISION = 5
    def __init__(self, username:str, password:str, app_key:str, base_url:str="https://ciapi.fxcorporate.com/tradeapi", account_id:str|None=None, timeout:int=20, max_retries:int=2):
        self.username=username; self.password=password; self.app_key=app_key
        self.base_url=base_url.rstrip("/"); self.account_id=account_id
        self.timeout=timeout; self.max_retries=max_retries
        self._s = requests.Session()
        self._s.headers.update({"Content-Type":"application/json"})
    def _url(self,p:str)->str:
        return self.base_url + (p if p.startswith("/") else "/" + p)
    def _req(self,m:str,p:str,*,params=None,json_body=None,expected=(200,)):
        last=None
        for i in range(self.max_retries+1):
            try:
                r=self._s.request(m.upper(), self._url(p), params=params, data=None if json_body is None else json.dumps(json_body), timeout=self.timeout)
                if r.status_code not in (expected if isinstance(expected,tuple) else (expected,)):
                    try: payload=r.json()
                    except Exception: payload={"text": r.text}
                    raise APIError(f"HTTP {r.status_code} {m} {p}: {payload}")
                try: return r.json()
                except Exception: return r.text
            except Exception as e:
                last=e; time.sleep(0.5*(i+1))
        raise APIError(f"Request failed: {last}")
    def login(self)->None:
        self._req("POST","/session", json_body={"UserName":self.username,"Password":self.password,"AppKey":self.app_key}, expected=(200,201))
    def logout(self)->None:
        try: self._req("DELETE","/session", expected=(200,204))
        except Exception: pass
    def get_balance(self)->Dict[str,Any]:
        data=self._req("GET","/accounts", expected=200)
        accounts = data["Accounts"] if isinstance(data,dict) and "Accounts" in data else (data if isinstance(data,list) else [data])
        acct = accounts[0] if accounts else {}
        return {
            "AccountId": acct.get("AccountId") or acct.get("id") or acct.get("account_id"),
            "Balance": acct.get("Balance") or acct.get("balance") or acct.get("Equity") or acct.get("equity"),
            "Equity": acct.get("Equity") or acct.get("equity"),
            "Raw": acct,
        }
    def get_price(self, interval:str="1m")->float:
        data=self._req("GET", f"/pricebars/{self.SYMBOL.replace(' ','')}?num=1&interval={interval}", expected=200)
        if isinstance(data,list) and data:
            bar=data[-1]; price=float(bar.get("Close") or bar.get("close") or bar.get("bidClose") or bar.get("askClose"))
            return round(price, self.PRECISION)
        raise APIError(f"Unexpected price payload: {data}")