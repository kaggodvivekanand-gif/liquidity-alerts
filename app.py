
bash

cat /home/claude/liquidity-alerts/app.py
Output

import requests
import time
import threading
import yfinance as yf
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8512324275:AAGkdCxomee2UXgrSvgwFqEOmgbEOENJFwg"
TELEGRAM_CHAT_ID   = "733306778"
SYMBOLS      = ["GC=F", "SI=F"]
SYMBOL_NAMES = {"GC=F": "XAUUSD (Gold)", "SI=F": "XAGUSD (Silver)"}
TIMEFRAME    = "15m"
MULT         = 3
CHECK_EVERY  = 60
LOOKBACK     = 10

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
alerted = set()
last_scan = {"time": "Not yet", "status": "Starting..."}


def send_telegram(message):
    try:
        requests.post(TELEGRAM_URL, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"[Telegram error] {e}")


def fetch_candles(symbol, interval, period="5d"):
    try:
        df = yf.download(symbol, interval=interval, period=period,
                         auto_adjust=True, progress=False)
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower()
                      for c in df.columns]
        return df.dropna()
    except Exception as e:
        print(f"[Fetch error] {symbol}: {e}")
        return pd.DataFrame()


def detect_swings(df, mult):
    swings = []
    highs = df["high"].values
    lows  = df["low"].values
    group_highs, group_lows, group_idx = [], [], []
    for i in range(0, len(df) - mult, mult):
        group_highs.append(max(highs[i:i+mult]))
        group_lows.append(min(lows[i:i+mult]))
        group_idx.append(df.index[i])
    for i in range(1, len(group_highs) - 1):
        if group_highs[i] > group_highs[i-1] and group_highs[i] > group_highs[i+1]:
            swings.append((group_idx[i], group_highs[i], "bearish"))
        if group_lows[i] < group_lows[i-1] and group_lows[i] < group_lows[i+1]:
            swings.append((group_idx[i], group_lows[i], "bullish"))
    return swings


def format_message(symbol, swing_type, price, tf, ts):
    name = SYMBOL_NAMES.get(symbol, symbol)
    emoji, direction, label = ("🔴","Bearish","Resistance level") if swing_type == "bearish" else ("🟢","Bullish","Support level")
    time_str = ts.strftime("%Y-%m-%d %H:%M UTC") if hasattr(ts, "strftime") else str(ts)
    return (
        f"{emoji} <b>AlgoAlpha — {direction} Swing Liquidity Formed</b>\n\n"
        f"📌 <b>Ticker:</b> {name}\n"
        f"⏱ <b>Timeframe:</b> {tf}\n"
        f"💰 <b>{label}:</b> {round(price, 3)}\n"
        f"🕐 <b>Time:</b> {time_str}"
    )


def scan():
    for symbol in SYMBOLS:
        df = fetch_candles(symbol, TIMEFRAME)
        if df.empty or len(df) < MULT * 3:
            continue
        swings = detect_swings(df, MULT)
        for ts, price, swing_type in swings[-LOOKBACK:]:
            key = f"{symbol}_{swing_type}_{round(price, 3)}"
            if key not in alerted:
                alerted.add(key)
                send_telegram(format_message(symbol, swing_type, price, TIMEFRAME, ts))
                print(f"[ALERT] {SYMBOL_NAMES.get(symbol, symbol)} {swing_type} @ {price}")


def scanner_loop():
    send_telegram(
        "✅ <b>AlgoAlpha Scanner Started</b>\n\n"
        "📌 Monitoring: XAUUSD (Gold), XAGUSD (Silver)\n"
        "⏱ Timeframe: 15m\n"
        "🔄 Checking every 60 seconds\n"
        "📊 Alerting: 🟢 Bullish + 🔴 Bearish swings"
    )
    while True:
        try:
            now = datetime.utcnow().strftime("%H:%M:%S")
            print(f"\n[{now}] Scanning...")
            last_scan["time"] = now
            scan()
            last_scan["status"] = "OK"
        except Exception as e:
            last_scan["status"] = f"Error: {e}"
            print(f"[ERROR] {e}")
        time.sleep(CHECK_EVERY)


# Flask keeps the web service alive on Render free tier
@app.route("/")
def index():
    return jsonify({
        "status": "running",
        "last_scan": last_scan["time"],
        "scanner_status": last_scan["status"],
        "symbols": list(SYMBOL_NAMES.values())
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# Start scanner in background thread when app starts
t = threading.Thread(target=scanner_loop, daemon=True)
t.start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
