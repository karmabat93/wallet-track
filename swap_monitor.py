
import os
import time
import requests
import json
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY")

POLL_INTERVAL = 15  # secondes
TX_HISTORY = {}

def load_addresses():
    with open("addresses.json", "r") as f:
        return json.load(f)["wallets"]

def fetch_transactions(address):
    url = f"https://api.basescan.org/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": BASESCAN_API_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data["status"] == "1":
            return data["result"]
    except Exception as e:
        print(f"[{address}] Erreur API: {e}")
    return []

def is_swap(tx):
    return tx["to"] and tx["input"] and tx["isError"] == "0" and int(tx["value"]) == 0

def format_tx(tx):
    return {
        "hash": tx["hash"],
        "from": tx["from"],
        "to": tx["to"],
        "timestamp": datetime.utcfromtimestamp(int(tx["timeStamp"])).strftime("%Y-%m-%d %H:%M:%S"),
        "method": tx["functionName"] or "Swap",
        "gas": int(tx["gasUsed"]),
        "block": tx["blockNumber"]
    }

def notify_discord(tx, address):
    content = f"🔁 **Swap détecté**

"
    content += f"📤 From: `{tx['from']}`
"
    content += f"📥 To: `{tx['to']}`
"
    content += f"🕒 Time: `{tx['timestamp']}`
"
    content += f"⛽ Gas used: `{tx['gas']}`
"
    content += f"[🔗 Voir la transaction](https://basescan.org/tx/{tx['hash']})"
    payload = {"content": content}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur Discord: {e}")

def main():
    global TX_HISTORY
    print("🔍 Lancement du monitoring de swaps...")
    while True:
        addresses = load_addresses()
        for address in addresses:
            txs = fetch_transactions(address)
            if not txs:
                continue
            last_hash = TX_HISTORY.get(address)
            if txs[0]["hash"] != last_hash:
                for tx in txs[:3]:
                    if is_swap(tx) and tx["hash"] != last_hash:
                        data = format_tx(tx)
                        notify_discord(data, address)
                        TX_HISTORY[address] = tx["hash"]
                        break
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
