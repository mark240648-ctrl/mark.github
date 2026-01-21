import streamlit as st
import yfinance as yf
import pandas as pd
import ta
from streamlit.components.v1 import iframe

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(layout="wide")
st.title("แดชบอร์ดเทรดหุ้น AI / อวกาศ / ทองคำ")

# ------------------------------
# Tickers (แก้ GOLD → XAUUSD=X)
# ------------------------------
TICKERS = [
    "NDAQ", "TSLA", "ASML", "GOOGL", "AVGO", "AMZN",
    "EOSE", "AAPL", "RKLB", "INOD", "IREN",
    "ORCL", "ONDS", "PL",
    "XAUUSD=X"   # ✅ Gold Spot
]

# ------------------------------
# Action Logic
# ------------------------------
def action(conf):
    if conf >= 70:
        return "Long ✅"
    elif conf >= 50:
        return "Speculative ⚡"
    else:
        return "Hold ⚠️"

# ------------------------------
# Fetch data (Fallback version)
# ------------------------------
@st.cache_data(ttl=600)
def fetch_data(tickers):
    rows = []
    failed = []

    for t in tickers:
        try:
            df = yf.Ticker(t).history(period="6mo", interval="1d")

            if df.empty or len(df) < 20:
                failed.append(t)
                continue

            close = df["Close"]
            volume = df["Volume"]

            rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
            macd = ta.trend.MACD(close).macd_diff().iloc[-1]
            vol_spike = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]

            score = 0
            if rsi < 30:
                score += 30
            elif rsi < 50:
                score += 15
            elif rsi < 70:
                score += 10

            if macd > 0:
                score += 30

            if vol_spike > 1.5:
                score += 40
            elif vol_spike > 1.1:
                score += 20

            confidence = min(score, 100)

            rows.append({
                "หุ้น": t,
                "ราคา": round(close.iloc[-1], 2),
                "RSI": round(rsi, 1),
                "MACD": round(macd, 3),
                "Volume Spike": round(vol_spike, 2),
                "ความมั่นใจ (%)": confidence
            })

        except Exception:
            failed.append(t)

    return pd.DataFrame(rows), failed

# ------------------------------
# Load
# ------------------------------
df, failed = fetch_data(TICKERS)

if df.empty:
    st.error("ไม่สามารถโหลดข้อมูลหุ้นได้ (Yahoo Finance ไม่ตอบสนอง)")
    st.stop()

# ------------------------------
# Show warning (fallback)
# ------------------------------
if failed:
    st.warning(f"⚠️ โหลดข้อมูลไม่สำเร็จ: {', '.join(failed)}")

# ------------------------------
# Action
# ------------------------------
df["คำแนะนำ"] = df["ความมั่นใจ (%)"].apply(action)

# ------------------------------
# Table
# ------------------------------
st.subheader("📊 Stock Ranking")

st.dataframe(
    df.sort_values("ความมั่นใจ (%)", ascending=False),
    use_container_width=True
)

# ------------------------------
# TradingView Chart
# ------------------------------
st.subheader("📈 TradingView Candlestick")

selected = st.selectbox("เลือกสินทรัพย์", df["หุ้น"].tolist())

tv_symbol = selected.replace("=X", "")  # TradingView format

tv_html = f"""
<!-- TradingView Widget -->
<div class="tradingview-widget-container">
  <div id="tv_chart"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "width": "100%",
    "height": 600,
    "symbol": "{tv_symbol}",
    "interval": "D",
    "timezone": "Etc/UTC",
    "theme": "dark",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#1e222d",
    "enable_publishing": false,
    "allow_symbol_change": true,
    "container_id": "tv_chart"
  }});
  </script>
</div>
"""

iframe(tv_html, height=620, scrolling=False)
