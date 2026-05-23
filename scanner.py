import requests
import time
import yfinance as yf
import pandas as pd
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8512324275:AAGkdCxomee2UXgrSvgwFqEOmgbEOENJFwg"
TELEGRAM_CHAT_ID   = "733306778"
SYMBOLS    = ["GC=F", "SI=F"]
SYMBOL_NAMES = {"GC=F": "XAUUSD (Gold)", "SI=F": "XAGUSD (Silver)"}
TIMEFRAME  = "15m"
MULT       = 3
CHECK_EVERY = 60
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
alerted = {}

def send_telegram(message):
    try:
        requests.post(TELEGRAM_URL, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"[Telegram error] {e}")

def fetch_candles(symbol, interval, period="2d"):
    try:
        df = yf.download(symbol, interval=interval, period=period, auto_adjust=True, progress=False)
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
        return df.dropna()
    except Exception as e:
        print(f"[Fetch error] {symbol}: {e}")
        return pd.DataFrame()

def detect_swings(df, mult):
    swings = []
    highs = df["high"].values
    lows  = df["low"].values
    n = len(df)
    group_highs, group_lows, group_idx = [], [], []
    for i in range(0, n - mult, mult):
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
    emoji, direction, label = ("🔴", "Bearish", "Resistance level") if swing_type == "bearish" else ("🟢", "Bullish", "Support level")
    time_str = ts.strftime("%Y-%m-%d %H:%M UTC") if hasattr(ts, "strftime") else str(ts)
    return f"{emoji} <b>AlgoAlpha — {direction} Swing Liquidity Formed</b>\n\n📌 <b>Ticker:</b> {name}\n⏱ <b>Timeframe:</b> {tf}\n💰 <b>{label}:</b> {round(price, 3)}\n🕐 <b>Time:</b> {time_str}"

def scan():
    for symbol in SYMBOLS:
        df = fetch_candles(symbol, TIMEFRAME)
        if df.empty or len(df) < MULT * 3:
            continue
        swings = detect_swings(df, MULT)
        if not swings:
            continue
        ts, price, swing_type = swings[-1]
        key = f"{symbol}_{swing_type}_{round(price, 3)}"
        if key not in alerted:
            alerted[key] = True
            send_telegram(format_message(symbol, swing_type, price, TIMEFRAME, ts))
            print(f"[ALERT] {SYMBOL_NAMES.get(symbol, symbol)} {swing_type} @ {price}")
        else:
            print(f"[SKIP]  {SYMBOL_NAMES.get(symbol, symbol)} {swing_type} @ {price}")

def main():
    print("Scanner started")
    send_telegram("✅ <b>AlgoAlpha Scanner Started</b>\n\n📌 Monitoring: XAUUSD (Gold), XAGUSD (Silver)\n⏱ Timeframe: 15m\n🔄 Checking every 60 seconds")
    while True:
        try:
            print(f"\n[{datetime.utcnow().strftime('%H:%M:%S')}] Scanning...")
            scan()
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(CHECK_EVERY)

if __name__ == "__main__":
    main()
