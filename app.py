import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import mplfinance as mpf

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(layout="wide")
st.title("แดชบอร์ดเทรดหุ้น AI / อวกาศ / ทองคำ")

# ------------------------------
# หุ้นที่ติดตาม
# ------------------------------
TICKERS = [
    "NDAQ", "TSLA", "ASML", "GOOGL", "AVGO", "AMZN",
    "EOSE", "AAPL", "RKLB", "INOD", "IREN",
    "ORCL", "OKLO", "ONDS", "PL", "GOLD"
]

# ------------------------------
# ฟังก์ชันคำนวณ Action
# ------------------------------
def action(conf):
    if conf >= 70:
        return "Long ✅"
    elif conf >= 50:
        return "Speculative ⚡"
    else:
        return "Hold ⚠️"

# ------------------------------
# ดึงข้อมูลหุ้น
# ------------------------------
@st.cache_data(ttl=600)
def fetch_data(tickers):
    rows = []

    for t in tickers:
        try:
            df = yf.download(t, period="6mo", interval="1d", progress=False)

            if df.empty or len(df) < 30:
                continue

            close = df["Close"]
            volume = df["Volume"]

            # ===== Indicators =====
            rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

            macd_ind = ta.trend.MACD(close)
            macd = macd_ind.macd_diff().iloc[-1]

            vol_spike = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]

            # ===== Confidence =====
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
                "ความมั่นใจ (%)": confidence,
                "History": df
            })

        except Exception:
            continue

    return pd.DataFrame(rows)

# ------------------------------
# โหลดข้อมูล
# ------------------------------
df = fetch_data(TICKERS)

# ------------------------------
# Guard ป้องกัน Error
# ------------------------------
if df.empty:
    st.error("ไม่สามารถโหลดข้อมูลหุ้นได้")
    st.stop()

if "ความมั่นใจ (%)" not in df.columns:
    st.error("ข้อมูลความมั่นใจไม่ถูกสร้าง")
    st.write(df.columns)
    st.stop()

# ------------------------------
# Action
# ------------------------------
df["คำแนะนำ"] = df["ความมั่นใจ (%)"].apply(action)

# ------------------------------
# แสดงตาราง
# ------------------------------
st.subheader("📊 Stock Ranking")

st.dataframe(
    df[
        ["หุ้น", "ราคา", "RSI", "MACD", "Volume Spike", "ความมั่นใจ (%)", "คำแนะนำ"]
    ].sort_values("ความมั่นใจ (%)", ascending=False),
    use_container_width=True
)

# ------------------------------
# เลือกหุ้นดูกราฟ
# ------------------------------
st.subheader("📈 Candlestick + RSI + MACD")

selected = st.selectbox("เลือกหุ้น", df["หุ้น"].tolist())
hist = df.loc[df["หุ้น"] == selected, "History"].iloc[0]

# ===== เพิ่ม Indicator ในกราฟ =====
hist["EMA20"] = ta.trend.EMAIndicator(hist["Close"], 20).ema_indicator()
hist["EMA50"] = ta.trend.EMAIndicator(hist["Close"], 50).ema_indicator()
hist["RSI"] = ta.momentum.RSIIndicator(hist["Close"]).rsi()

macd_ind = ta.trend.MACD(hist["Close"])
hist["MACD"] = macd_ind.macd()
hist["MACD_signal"] = macd_ind.macd_signal()

# ===== Plot =====
apds = [
    mpf.make_addplot(hist["EMA20"]),
    mpf.make_addplot(hist["EMA50"]),
    mpf.make_addplot(hist["RSI"], panel=1, ylabel="RSI"),
    mpf.make_addplot(hist["MACD"], panel=2, ylabel="MACD"),
    mpf.make_addplot(hist["MACD_signal"], panel=2),
]

mpf.plot(
    hist,
    type="candle",
    style="charles",
    addplot=apds,
    volume=True,
    panel_ratios=(3, 1, 1),
    figsize=(14, 8),
    show_nontrading=False
)
