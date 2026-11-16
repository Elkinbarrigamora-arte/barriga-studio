#!/usr/bin/env python3
"""PoYo Wan 2.2 Fast adapter for Barriga Studio (safe by default).

Dry-run is the default. This CLI never stores the API key in source control.
Live generations require --confirm-charge and POYO_API_KEY.
The local budget ledger is an estimate, not a provider-side spending cap.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api.poyo.ai/api/generate"
MODEL = "wan2.2-text-to-video-fast"
PRICE_USD = {"480p": 0.03, "720p": 0.06}
LIMIT_USD = 5.00
LEDGER = Path.home() / ".barriga-studio" / "poyo-budget.json"


def request_json(url, key, payload=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST" if data is not None else "GET", headers=headers)
    try:
        with urlopen(req, timeout=40) as response:
            result = json.load(response)
    except HTTPError as err:
        raise RuntimeError(f"PoYo HTTP {err.code}") from err
    except (URLError, TimeoutError, OSError, ValueError) as err:
        raise RuntimeError(f"PoYo connection/response error: {type(err).__name__}") from err
    if result.get("code") != 200:
        raise RuntimeError(f"PoYo code {result.get('code')}: {result.get('message', 'request rejected')}")
    return result.get("data") or {}


def read_ledger():
    if LEDGER.is_file():
        obj = json.loads(LEDGER.read_text(encoding="utf-8"))
        return {"reserved_usd": float(obj["reserved_usd"]), "tasks": obj["tasks"]}
    return {"reserved_usd": 0.0, "tasks": []}


def save_ledger(ledger):
    LEDGER.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    LEDGER.chmod(0o600)


def main():
    p = argparse.ArgumentParser(description="Barriga Studio: PoYo 480p adapter")
    p.add_argument("--prompt", help="Text prompt, max 800 characters")
    p.add_argument("--resolution", choices=("480p", "720p"), default="480p")
    p.add_argument("--status", metavar="TASK_ID", help="Query an existing task without charge")
    p.add_argument("--confirm-charge", action="store_true", help="Explicitly allow one paid submission")
    args = p.parse_args()
    if args.status:
        key = os.environ.get("POYO_API_KEY")
        if not key:
            p.error("Set POYO_API_KEY locally to query status")
        if not args.status.replace("-", "").replace("_", "").isalnum():
            p.error("Invalid task ID")
        print(json.dumps(request_json(f"{BASE}/status/{args.status}", key), indent=2))
        return
    if not args.prompt or not 1 <= len(args.prompt) <= 800:
        p.error("Provide --prompt of 1 to 800 characters")
    payload = {"model": MODEL, "input": {
        "prompt": args.prompt, "aspect_ratio": "9:16", "resolution": args.resolution
    }}
    cost = PRICE_USD[args.resolution]
    if not args.confirm_charge:
        print(json.dumps({"mode": "DRY_RUN_NO_CHARGE", "estimate_usd": cost,
                          "budget_usd": LIMIT_USD, "payload": payload}, indent=2))
        return
    key = os.environ.get("POYO_API_KEY")
    if not key:
        p.error("Set POYO_API_KEY locally; never put keys in source code or chat")
    ledger = read_ledger()
    if ledger["reserved_usd"] + cost > LIMIT_USD + 1e-9:
        p.error("Local budget estimate would exceed $5. Do not submit.")
    # Record the reservation BEFORE submitting to prevent retries after uncertain network errors.
    ledger["reserved_usd"] = round(ledger["reserved_usd"] + cost, 2)
    ledger["tasks"].append({"task_id": None, "cost_usd": cost, "state": "submission_pending"})
    save_ledger(ledger)
    data = request_json(f"{BASE}/submit", key, payload)
    task_id = data.get("task_id")
    ledger["tasks"][-1].update({"task_id": task_id, "state": data.get("status", "submitted")})
    save_ledger(ledger)
    print(json.dumps({"task_id": task_id, "estimated_charged_or_reserved_usd": cost,
                      "reserved_budget_usd": ledger["reserved_usd"],
                      "note": "Use --status TASK_ID; completed media is in files"}, indent=2))


if __name__ == "__main__":
    main()
