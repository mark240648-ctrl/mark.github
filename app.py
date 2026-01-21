import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import ta
import mplfinance as mpf

st.set_page_config(layout="wide")
st.title("AI / Space / Gold Trading Dashboard")

# -------------------------------
# หุ้นตามธีม
# -------------------------------
tickers = [
    "NDAQ","TSLA","ASML","GOOGL","AVGO","AMZN","AAPL","ORCL",
    "RKLB","ONDS",
    "EOSE","IREN","OKLO",
    "INOD",
    "GLD"
]

# -------------------------------
# News Sentiment
# -------------------------------
def fetch_news_score(keyword):
    url = f"https://news.google.com/rss/search?q={keyword}"
    score = 0
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.content, "xml")
        for item in soup.find_all("item")[:3]:
            title = item.title.text.lower()
            if any(w in title for w in ["growth","profit","bullish","surge"]):
                score += 10
            if any(w in title for w in ["risk","loss","bearish","decline"]):
                score -= 10
    except:
        pass
    return score

# -------------------------------
# Fetch Data
# -------------------------------
@st.cache_data(ttl=600)
def fetch_stock_data(tickers):
    rows = []

    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="1y")
            if len(hist) < 60:
                continue

            # EMA
            hist["EMA20"] = ta.trend.EMAIndicator(hist["Close"], 20).ema_indicator()
            hist["EMA50"] = ta.trend.EMAIndicator(hist["Close"], 50).ema_indicator()
            hist["EMA100"] = ta.trend.EMAIndicator(hist["Close"], 100).ema_indicator()
            hist["EMA200"] = ta.trend.EMAIndicator(hist["Close"], 200).ema_indicator()

            # RSI
            hist["RSI"] = ta.momentum.RSIIndicator(hist["Close"], 14).rsi()
            rsi = hist["RSI"].iloc[-1]

            # MACD
            macd = ta.trend.MACD(hist["Close"])
            hist["MACD"] = macd.macd()
            hist["MACD_signal"] = macd.macd_signal()

            macd_now = hist["MACD"].iloc[-1]
            macd_sig = hist["MACD_signal"].iloc[-1]
            macd_prev = hist["MACD"].iloc[-2]
            macd_sig_prev = hist["MACD_signal"].iloc[-2]

            # Volume Spike
            avg_vol = hist["Volume"].rolling(20).mean().iloc[-1]
            vol_ratio = hist["Volume"].iloc[-1] / max(avg_vol, 1)

            # Scores
            rsi_score = 15 if rsi < 30 else 10 if rsi < 50 else -10 if rsi > 70 else 5
            macd_score = 15 if macd_prev < macd_sig_prev and macd_now > macd_sig else -15 if macd_prev > macd_sig_prev and macd_now < macd_sig else 5 if macd_now > macd_sig else 0
            vol_score = 15 if vol_ratio > 2 else 8 if vol_ratio > 1.5 else 0

            news_score = fetch_news_score(t)

            total_score = rsi_score + macd_score + vol_score + news_score

            # Alert
            alert = "—"
            if rsi < 40 and macd_prev < macd_sig_prev and macd_now > macd_sig and vol_ratio > 1.5:
                alert = "🔥 BUY SIGNAL"
            elif rsi > 70 and macd_prev > macd_sig_prev and macd_now < macd_sig:
                alert = "⚠️ SELL SIGNAL"

            # Confidence %
            confidence = 0
            if 40 < rsi < 65: confidence += 20
            if macd_now > macd_sig: confidence += 30
            if vol_ratio > 1.5: confidence += 20
            if hist["EMA20"].iloc[-1] > hist["EMA50"].iloc[-1]: confidence += 20
            confidence += min(max(news_score, -10), 10)
            confidence = min(confidence, 100)

            rows.append({
                "Ticker": t,
                "Price": round(hist["Close"].iloc[-1],2),
                "RSI": round(rsi,1),
                "MACD": round(macd_now,3),
                "Volume Spike": round(vol_ratio,2),
                "Total Score": total_score,
                "Confidence %": confidence,
                "Alert": alert,
                "History": hist
            })
        except:
            continue

    return pd.DataFrame(rows)

df = fetch_stock_data(tickers)

# -------------------------------
# Action
# -------------------------------
def action(conf):
    if conf >= 80:
        return "Strong Long 🚀"
    elif conf >= 60:
        return "Long ✅"
    elif conf >= 45:
        return "Speculative ⚡"
    else:
        return "Hold ⚠️"

df["Action"] = df["Confidence %"].apply(action)

# -------------------------------
# Dashboard
# -------------------------------
st.subheader("Stock Ranking")
st.dataframe(
    df[["Ticker","Price","RSI","MACD","Volume Spike","Confidence %","Alert","Action"]]
    .sort_values("Confidence %", ascending=False)
)

# -------------------------------
# Chart
# -------------------------------
st.subheader("Candlestick + EMA + RSI + MACD")

selected = st.selectbox("Select Stock", df["Ticker"])
hist = df[df["Ticker"] == selected]["History"].values[0]

apds = [
    mpf.make_addplot(hist["EMA20"]),
    mpf.make_addplot(hist["EMA50"]),
    mpf.make_addplot(hist["EMA100"]),
    mpf.make_addplot(hist["EMA200"]),
    mpf.make_addplot(hist["RSI"], panel=1, ylabel="RSI"),
    mpf.make_addplot([70]*len(hist), panel=1, linestyle="--"),
    mpf.make_addplot([30]*len(hist), panel=1, linestyle="--"),
    mpf.make_addplot(hist["MACD"], panel=2, ylabel="MACD"),
    mpf.make_addplot(hist["MACD_signal"], panel=2),
]

mpf.plot(
    hist,
    type="candle",
    addplot=apds,
    volume=True,
    panel_ratios=(3,1,1),
    style="charles",
    title=f"{selected} Technical Chart",
    show_nontrading=False
)
