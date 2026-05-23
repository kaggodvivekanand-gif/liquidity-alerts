from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8512324275:AAGkdCxomee2UXgrSvgwFqEOmgbEOENJFwg")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "733306778")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def send_telegram(message: str):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    resp = requests.post(TELEGRAM_URL, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()

def format_message(data: dict) -> str:
    alert_type = data.get("type", "unknown")
    ticker     = data.get("ticker", "N/A")
    price      = data.get("price", "N/A")
    tf         = data.get("tf", "N/A")
    time_raw   = data.get("time", "")

    try:
        ts = datetime.utcfromtimestamp(int(time_raw) / 1000)
        time_str = ts.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        time_str = time_raw or "N/A"

    if alert_type == "bearish_swing":
        emoji     = "🔴"
        direction = "Bearish"
        label     = "Resistance level"
    elif alert_type == "bullish_swing":
        emoji     = "🟢"
        direction = "Bullish"
        label     = "Support level"
    else:
        emoji     = "⚪"
        direction = "Unknown"
        label     = "Level"

    return (
        f"{emoji} <b>AlgoAlpha — {direction} Swing Liquidity Formed</b>\n\n"
        f"📌 <b>Ticker:</b> {ticker}\n"
        f"⏱ <b>Timeframe:</b> {tf}\n"
        f"💰 <b>{label}:</b> {price}\n"
        f"🕐 <b>Time:</b> {time_str}"
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid or empty JSON payload"}), 400

    alert_type = data.get("type", "")
    if alert_type not in ("bearish_swing", "bullish_swing"):
        return jsonify({"error": f"Unknown alert type: {alert_type}"}), 400

    try:
        message = format_message(data)
        send_telegram(message)
        print(f"[OK] Sent {alert_type} alert for {data.get('ticker')}")
        return jsonify({"status": "sent"}), 200
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Telegram send failed: {e}")
        return jsonify({"error": "Telegram delivery failed"}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
