import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide")
st.title("แดชบอร์ดเทรดหุ้น AI / อวกาศ / ทองคำ")

# -------------------------------
# รายชื่อหุ้น
# -------------------------------
tickers = [
    "NDAQ","TSLA","ASML","GOOGL","AVGO","AMZN","AAPL","ORCL",
    "RKLB","ONDS",
    "EOSE","IREN","OKLO",
    "INOD",
    "GLD"
]

# -------------------------------
# ข่าว + Sentiment
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
# ดึงข้อมูลหุ้น
# -------------------------------
@st.cache_data(ttl=600)
def fetch_stock_data(tickers):
    rows = []

    for t in tickers:
        try:
            hist = yf.download(t, period="1y", progress=False)
            if len(hist) < 60:
                continue

            # EMA
            hist["EMA20"] = ta.trend.EMAIndicator(hist["Close"], 20).ema_indicator()
            hist["EMA50"] = ta.trend.EMAIndicator(hist["Close"], 50).ema_indicator()
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

            # คะแนน
            rsi_score = 15 if rsi < 30 else 10 if rsi < 50 else -10 if rsi > 70 else 5
            macd_score = 15 if macd_prev < macd_sig_prev and macd_now > macd_sig else \
                         -15 if macd_prev > macd_sig_prev and macd_now < macd_sig else \
                         5 if macd_now > macd_sig else 0
            vol_score = 15 if vol_ratio > 2 else 8 if vol_ratio > 1.5 else 0
            news_score = fetch_news_score(t)

            total_score = rsi_score + macd_score + vol_score + news_score

            # Alert
            alert = "—"
            if rsi < 40 and macd_prev < macd_sig_prev and macd_now > macd_sig and vol_ratio > 1.5:
                alert = "🔥 สัญญาณซื้อ"
            elif rsi > 70 and macd_prev > macd_sig_prev and macd_now < macd_sig:
                alert = "⚠️ สัญญาณขาย"

            # Confidence %
            confidence = 0
            if 40 < rsi < 65: confidence += 20
            if macd_now > macd_sig: confidence += 30
            if vol_ratio > 1.5: confidence += 20
            if hist["EMA20"].iloc[-1] > hist["EMA50"].iloc[-1]: confidence += 20
            confidence += min(max(news_score, -10), 10)
            confidence = min(confidence, 100)

            rows.append({
                "หุ้น": t,
                "ราคา": round(hist["Close"].iloc[-1],2),
                "RSI": round(rsi,1),
                "MACD": round(macd_now,3),
                "ปริมาณซื้อขายพุ่ง": round(vol_ratio,2),
                "ความมั่นใจ (%)": confidence,
                "สัญญาณเตือน": alert,
                "History": hist
            })
        except:
            continue

    return pd.DataFrame(rows)

df = fetch_stock_data(tickers)

# -------------------------------
# คำแนะนำ
# -------------------------------
def action(conf):
    if conf >= 80:
        return "Strong Long 🚀"
    elif conf >= 60:
        return "Long ✅"
    elif conf >= 45:
        return "เก็งกำไร ⚡"
    else:
        return "รอดูสถานการณ์ ⚠️"

df["คำแนะนำ"] = df["ความมั่นใจ (%)"].apply(action)

# -------------------------------
# ตารางจัดอันดับ
# -------------------------------
st.subheader("📊 จัดอันดับหุ้น")
st.dataframe(
    df[["หุ้น","ราคา","RSI","MACD","ปริมาณซื้อขายพุ่ง","ความมั่นใจ (%)","สัญญาณเตือน","คำแนะนำ"]]
    .sort_values("ความมั่นใจ (%)", ascending=False)
)

# -------------------------------
# กราฟแท่งเทียน (TradingView style)
# -------------------------------
st.subheader("📈 กราฟแท่งเทียน (สไตล์ TradingView)")

if df.empty:
    st.stop()

selected = st.selectbox("เลือกหุ้น", df["หุ้น"].tolist())
hist = df.loc[df["หุ้น"] == selected, "History"].iloc[0]


fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    row_heights=[0.6,0.2,0.2],
    vertical_spacing=0.02
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=hist.index,
        open=hist["Open"],
        high=hist["High"],
        low=hist["Low"],
        close=hist["Close"],
        name="ราคา"
    ),
    row=1, col=1
)

# EMA
fig.add_trace(go.Scatter(x=hist.index, y=hist["EMA20"], name="EMA20"), row=1, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist["EMA50"], name="EMA50"), row=1, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist["EMA200"], name="EMA200"), row=1, col=1)

# RSI
fig.add_trace(go.Scatter(x=hist.index, y=hist["RSI"], name="RSI"), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", row=2, col=1)

# MACD
fig.add_trace(go.Scatter(x=hist.index, y=hist["MACD"], name="MACD"), row=3, col=1)
fig.add_trace(go.Scatter(x=hist.index, y=hist["MACD_signal"], name="Signal"), row=3, col=1)

fig.update_layout(
    template="plotly_dark",
    height=850,
    xaxis_rangeslider_visible=False,
    title=f"{selected} | กราฟเทคนิค (EMA / RSI / MACD)"
)

st.plotly_chart(fig, use_container_width=True)
