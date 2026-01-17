import streamlit as st
import yfinance as yf
import google.generativeai as genai
import feedparser
import pandas as pd
import plotly.graph_objects as go

# --- KONFIGURATION ---
st.set_page_config(page_title="Executive Dashboard", layout="wide")

# API Key Setup
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("API Key fehlt.")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- HILFSFUNKTIONEN ---

def get_market_data(ticker_symbol):
    """Holt Daten und berechnet RSI für ein Asset."""
    try:
        # Ticker-Mapping für Yahoo Finance
        symbols = {
            "Bitcoin": "BTC-EUR",
            "Ethereum": "ETH-EUR",
            "Gold": "GC=F",          # Gold Futures
            "MSCI World": "URTH"     # iShares MSCI World ETF als Proxy
        }
        
        t = yf.Ticker(symbols.get(ticker_symbol, ticker_symbol))
        hist = t.history(period="1mo")
        
        if hist.empty:
            return None

        # RSI Berechnung
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        return {
            "price": current_price,
            "change": change_pct,
            "rsi": rsi.iloc[-1],
            "history": hist['Close']
        }
    except Exception as e:
        return None

def create_gauge(value, title):
    """Erstellt einen Tacho mit Plotly."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},  # Buy Zone
                {'range': [30, 70], 'color': "lightgray"},  # Hold Zone
                {'range': [70, 100], 'color': "salmon"}],   # Sell Zone
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': value}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def get_combined_analysis(market_data_str, news_str):
    """Der EINE Aufruf, der alles analysiert."""
    prompt = f"""
    Du bist ein Senior Investment Advisor. Hier ist dein Morgen-Briefing.
    
    1. MARKTDATEN:
    {market_data_str}
    
    2. NEWS:
    {news_str}
    
    AUFGABE:
    Erstelle eine prägnante Zusammenfassung (Markdown).
    - Abschnitt 1: "Markt-Radar": Gib für jedes Asset (BTC, ETH, Gold, MSCI) EINEN Satz Einschätzung basierend auf RSI und Trend (z.B. "Bitcoin ist überkauft, Vorsicht ratsam").
    - Abschnitt 2: "News-Impact": Welche der News ist heute am relevantesten für Tech/Investments und warum?
    - Tonfall: Professionell, objektiv, direkt.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "KI-Dienst nicht erreichbar."

# --- HAUPTPROGRAMM ---

st.title("🚀 Executive Dashboard")

# 1. DATEN SAMMELN (Passiert im Hintergrund)
assets = ["Bitcoin", "Ethereum", "Gold", "MSCI World"]
market_results = {}
market_context_for_ai = ""

# Layout für die Assets (4 Spalten)
cols = st.columns(4)

for i, asset in enumerate(assets):
    data = get_market_data(asset)
    market_results[asset] = data
    
    with cols[i]:
        st.subheader(asset)
        if data:
            # Metrik anzeigen
            st.metric(label="Preis", value=f"{data['price']:,.2f}", delta=f"{data['change']:.2f}%")
            
            # Daten für AI String sammeln
            market_context_for_ai += f"{asset}: Preis={data['price']:.2f}, Änderung={data['change']:.2f}%, RSI={data['rsi']:.1f}\n"
            
            # Tacho anzeigen
            st.plotly_chart(create_gauge(data['rsi'], "RSI (Sentiment)"), use_container_width=True)
        else:
            st.error("Datenfehler")

st.divider()

# 2. NEWS & AI ANALYSE BEREICH
col_news, col_ai = st.columns([1, 2])

with col_news:
    st.subheader("📰 News Feed")
    rss_url = "https://www.heise.de/rss/heise-atom.xml"
    feed = feedparser.parse(rss_url)
    news_context_for_ai = ""
    
    for entry in feed.entries[:5]:
        st.markdown(f"• [{entry.title}]({entry.link})")
        news_context_for_ai += f"- {entry.title}\n"

with col_ai:
    st.subheader("🧠 KI Gesamt-Analyse")
    
    if st.button("Generiere Tages-Briefing (1 Token)"):
        with st.spinner('Der Agent analysiert Märkte & News...'):
            # Hier passiert der EINE Aufruf
            analysis = get_combined_analysis(market_context_for_ai, news_context_for_ai)
            st.markdown(analysis)
