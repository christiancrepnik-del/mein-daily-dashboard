import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
import plotly.graph_objects as go
from duckduckgo_search import DDGS

# --- KONFIGURATION ---
st.set_page_config(page_title="AI Research Dashboard", layout="wide")

# API Key Setup
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("API Key fehlt.")
    st.stop()

genai.configure(api_key=API_KEY)
# Wir bleiben beim schnellen Flash-Modell
model = genai.GenerativeModel('gemini-2.5-flash')

# --- TOOLS (Der "Werkzeugkasten" des Agenten) ---

def search_web(keywords, max_results=4):
    """Sucht aktiv im Web nach Informationen."""
    try:
        results = DDGS().text(keywords, max_results=max_results)
        summary = ""
        for r in results:
            summary += f"- Titel: {r['title']}\n  Inhalt: {r['body']}\n  Link: {r['href']}\n\n"
        return summary
    except Exception as e:
        return f"Fehler bei der Websuche: {e}"

def get_market_data(ticker_symbol):
    """Holt Finanzdaten & RSI."""
    try:
        symbols = {
            "Bitcoin": "BTC-EUR",
            "Ethereum": "ETH-EUR",
            "Gold": "GC=F",
            "MSCI World": "URTH"
        }
        t = yf.Ticker(symbols.get(ticker_symbol, ticker_symbol))
        hist = t.history(period="1mo")
        
        if hist.empty: return None

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
            "rsi": rsi.iloc[-1]
        }
    except:
        return None

def create_gauge(value, title):
    """Erstellt Tacho-Grafik."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "rgba(0, 255, 0, 0.3)"},
                {'range': [30, 70], 'color': "rgba(200, 200, 200, 0.3)"},
                {'range': [70, 100], 'color': "rgba(255, 0, 0, 0.3)"}],
        }
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
    return fig

# --- HAUPTPROGRAMM ---

st.title("🕵️‍♂️ Mein AI Research Agent")

# 1. MARKTDATEN (Live Charts)
st.subheader("1. Markt-Status")
assets = ["Bitcoin", "Ethereum", "Gold", "MSCI World"]
cols = st.columns(4)
market_data_string = ""

for i, asset in enumerate(assets):
    data = get_market_data(asset)
    with cols[i]:
        if data:
            st.metric(asset, f"{data['price']:,.0f}", f"{data['change']:.2f}%")
            st.plotly_chart(create_gauge(data['rsi'], "RSI"), use_container_width=True)
            market_data_string += f"{asset}: {data['change']:.2f}% (RSI: {data['rsi']:.1f})\n"

st.divider()

# 2. DER RECHERCHE AGENT
st.subheader("2. Recherche & Analyse")

col_input, col_result = st.columns([1, 2])

with col_input:
    st.info("Was soll ich heute recherchieren?")
    
    # Hier definierst du deine Themen-Prompts
    topic1 = st.text_input("Thema A", "Aktuelle AI Agents & LLM News heute")
    topic2 = st.text_input("Thema B", "Bitcoin Krypto Markt Analyse aktuell")
    
    start_btn = st.button("🚀 Recherche starten", type="primary")

with col_result:
    if start_btn:
        with st.status("Agent arbeitet...", expanded=True) as status:
            
            # A) Websuche ausführen
            status.write(f"🔍 Suche im Web nach: '{topic1}'...")
            web_results_1 = search_web(topic1)
            
            status.write(f"🔍 Suche im Web nach: '{topic2}'...")
            web_results_2 = search_web(topic2)
            
            # B) Alles an Gemini senden
            status.write("🧠 Analysiere Daten mit Gemini 2.5...")
            
            prompt = f"""
            Du bist mein persönlicher Research-Agent. Erstelle ein Executive Briefing.
            
            TEIL 1: FINANZ-CHECK (Daten: {market_data_string})
            - Kurze Einschätzung der Marktlage basierend auf RSI und Preisänderung.
            
            TEIL 2: RECHERCHE ERGEBNISSE
            Thema A: {topic1}
            Gefundene Infos: {web_results_1}
            
            Thema B: {topic2}
            Gefundene Infos: {web_results_2}
            
            ANWEISUNG:
            - Filtere unwichtige Werbung heraus.
            - Fasse die wichtigsten Erkenntnisse in Bulletpoints zusammen.
            - Gib eine Handlungsempfehlung oder ein Fazit ab.
            - Nutze Markdown Formatierung.
            """
            
            try:
                response = model.generate_content(prompt)
                st.markdown(response.text)
                status.update(label="Fertig!", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Fehler: {e}")
