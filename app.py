import streamlit as st
import yfinance as yf
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="株価テクニカル分析", layout="wide")
st.title("📈 株価テクニカル分析ダッシュボード")

# --- サイドバー：入力 ---
with st.sidebar:
    st.header("設定")
    ticker_input = st.text_input("銘柄コード（例：7203）", value="7203")
    period = st.selectbox("期間", ["3mo", "6mo", "1y", "2y"], index=1)
    st.caption("東証の銘柄コード（4桁）を入力してください")

ticker = ticker_input.strip() + ".T"

# --- データ取得 ---
@st.cache_data(ttl=300)
def load_data(ticker, period):
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if isinstance(df.columns, type(df.columns)) and df.columns.nlevels > 1:
        df.columns = df.columns.droplevel(1)
    return df

with st.spinner("データ取得中..."):
    df = load_data(ticker, period)

if df.empty:
    st.error("データが取得できませんでした。銘柄コードを確認してください。")
    st.stop()

# --- テクニカル指標計算 ---
df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
macd = ta.trend.MACD(close=df["Close"])
df["MACD"] = macd.macd()
df["MACD_signal"] = macd.macd_signal()
df["MACD_hist"] = macd.macd_diff()

# --- 銘柄情報 ---
info = yf.Ticker(ticker).info
company_name = info.get("longName") or info.get("shortName") or ticker_input
current_price = float(df["Close"].iloc[-1])
prev_price = float(df["Close"].iloc[-2])
change = current_price - prev_price
change_pct = (change / prev_price) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("銘柄", f"{ticker_input} {company_name[:15]}")
col2.metric("現在値", f"¥{current_price:,.0f}", f"{change:+.0f} ({change_pct:+.2f}%)")
col3.metric("RSI", f"{df['RSI'].iloc[-1]:.1f}")
col4.metric("MACD", f"{df['MACD'].iloc[-1]:.2f}")

# --- シグナル判定 ---
rsi_val = float(df["RSI"].iloc[-1])
macd_val = float(df["MACD"].iloc[-1])
macd_sig = float(df["MACD_signal"].iloc[-1])

st.subheader("シグナル判定")
if rsi_val < 30:
    st.success("🟢 RSI売られすぎ（買いシグナル）")
elif rsi_val > 70:
    st.error("🔴 RSI買われすぎ（売りシグナル）")
else:
    st.info("⚪ RSI 中立")

if macd_val > macd_sig:
    st.success("🟢 MACDゴールデンクロス（上昇トレンド）")
else:
    st.error("🔴 MACDデッドクロス（下降トレンド）")

# --- チャート描画 ---
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    row_heights=[0.55, 0.25, 0.2],
    vertical_spacing=0.03,
    subplot_titles=("ローソク足チャート", "MACD", "RSI")
)

fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="株価",
    increasing_line_color="#ef5350",
    decreasing_line_color="#26a69a"
), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#2196F3", width=1.5)), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="シグナル", line=dict(color="#FF9800", width=1.5)), row=2, col=1)
colors = ["#ef5350" if v >= 0 else "#26a69a" for v in df["MACD_hist"]]
fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="ヒストグラム", marker_color=colors), row=2, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="#9C27B0", width=1.5)), row=3, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)

fig.update_layout(
    height=700,
    showlegend=False,
    xaxis_rangeslider_visible=False,
    plot_bgcolor="#1e1e1e",
    paper_bgcolor="#1e1e1e",
    font=dict(color="#ffffff")
)
fig.update_xaxes(gridcolor="#333333")
fig.update_yaxes(gridcolor="#333333")

st.plotly_chart(fig, use_container_width=True)
st.caption("※ 本ツールは情報提供のみを目的としており、投資助言ではありません。")
