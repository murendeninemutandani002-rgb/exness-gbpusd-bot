# =============================================================================
# 🛡️ EXNESS ZAR GBPUSD GITHUB ACTIONS AUTOMATED BOT
# =============================================================================
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

import os
import json
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import requests
import yfinance as yf

# Configuration
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1565087883239366916/Iqt_eg212q59PrzNSQCHWFMhb0VDBvHdDiJWqZzYf-CXonDr3zt87CN062TSbr-lfNU_"
ACCOUNT_EQUITY_ZAR = 300.00
RISK_PER_TRADE_ZAR = 30.00
USD_ZAR_RATE = 18.25
SYMBOL = "GBPUSD"
TICKER = "GBPUSD=X"

def send_discord_alert(setup_type, entry, sl, tp, lots, risk_zar):
    SAST = timezone(timedelta(hours=2))
    sast_now = datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')

    embed_data = {
        "title": f"🚨 CLOUD SIGNAL DISPATCH: {SYMBOL} ({setup_type})",
        "color": 3066993 if "BUY" in setup_type else 15158332,
        "fields": [
            {"name": "Symbol", "value": SYMBOL, "inline": True},
            {"name": "Grade", "value": setup_type, "inline": True},
            {"name": "Risk (ZAR)", "value": f"R{risk_zar:.2f}", "inline": True},
            {"name": "Entry Price", "value": f"{entry:.5f}", "inline": True},
            {"name": "Stop Loss (SL)", "value": f"{sl:.5f}", "inline": True},
            {"name": "Take Profit (1:3 TP)", "value": f"{tp:.5f}", "inline": True},
            {"name": "Exness Lot Size", "value": f"{lots} Micro-lots", "inline": False}
        ],
        "footer": {"text": f"Exness Cloud Desk | SAST: {sast_now}"}
    }

    payload = {"embeds": [embed_data]}
    requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})

def run_cloud_scan():
    SAST = timezone(timedelta(hours=2))
    sast_now = datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')

    try:
        df = yf.download(TICKER, period="5d", interval="1h", progress=False)
        if df.empty:
            df = yf.download(TICKER, period="5d", interval="1d", progress=False)

        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                close_col = df['Close'].iloc[:, 0]
                high_col = df['High'].iloc[:, 0]
                low_col = df['Low'].iloc[:, 0]
            else:
                close_col = df['Close']
                high_col = df['High']
                low_col = df['Low']

            current_price = float(close_col.iloc[-1])
            hi = high_col.to_numpy(float)
            lo = low_col.to_numpy(float)
            cls = close_col.to_numpy(float)

            ema_fast = pd.Series(cls).ewm(span=50, adjust=False).mean().iloc[-1]
            ema_slow = pd.Series(cls).ewm(span=200, adjust=False).mean().iloc[-1]

            if current_price > ema_fast and current_price > ema_slow:
                bias = "LONG"
            elif current_price < ema_fast and current_price < ema_slow:
                bias = "SHORT"
            else:
                bias = "NEUTRAL"

            supports = [lo[i] for i in range(2, len(lo)-2) if lo[i] <= lo[max(0, i-2):min(len(lo), i+3)].min()]
            resistances = [hi[i] for i in range(2, len(hi)-2) if hi[i] >= hi[max(0, i-2):min(len(hi), i+3)].max()]
            sup = max([s for s in supports if s < current_price], default=current_price - 0.0050)
            res = min([r for r in resistances if r > current_price], default=current_price + 0.0050)

            pip = 0.0001
            digits = 5
            risk_amount_usd = RISK_PER_TRADE_ZAR / USD_ZAR_RATE
            pip_val_usd = 10.0

            dist_to_sup = abs(current_price - sup)
            dist_to_res = abs(current_price - res)
            zone_threshold = 0.0020

            if bias == "LONG":
                entry = round(current_price, digits)
                sl = round(sup - (15 * pip), digits)
                risk_distance = entry - sl
                tp = round(entry + (risk_distance * 3.0), digits)
                setup = "🔥 A+ BUY" if dist_to_sup <= zone_threshold else "⏳ WAIT"
            elif bias == "SHORT":
                entry = round(current_price, digits)
                sl = round(res + (15 * pip), digits)
                risk_distance = sl - entry
                tp = round(entry - (risk_distance * 3.0), digits)
                setup = "🔥 A+ SELL" if dist_to_res <= zone_threshold else "⏳ WAIT"
            else:
                entry = round(current_price, digits)
                sl = round(current_price - (20 * pip), digits)
                tp = round(current_price + (60 * pip), digits)
                setup = "⏳ WAIT"

            pip_risk = abs(entry - sl) / pip
            lots = max(0.01, round(risk_amount_usd / (pip_risk * pip_val_usd), 2))

            print(f"[{sast_now}] Px: {current_price:.5f} | Bias: {bias} | Status: {setup}")

            if setup in ["🔥 A+ BUY", "🔥 A+ SELL"]:
                send_discord_alert(setup, entry, sl, tp, lots, RISK_PER_TRADE_ZAR)
                print("🔥 A+ setup triggered and dispatched to Discord!")
            else:
                print("💤 No A+ trigger at this timestamp.")

    except Exception as e:
        print(f"Error during cloud scan: {e}")

if __name__ == "__main__":
    run_cloud_scan()