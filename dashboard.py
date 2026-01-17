import streamlit as st
import yfinance as yf
import google.generativeai as genai
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="Morning Briefing", layout="wide")

# Sicherheit: Key aus den Cloud-Secrets holen
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Kein API Key gefunden! Bitte in den Streamlit Secrets eintragen.")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- FUNKTIONEN ---
def get_ai_insight(context_data, topic):
    prompt = f"""
    Du bist ein objektiver Finanz- und Tech-Analyst.
    Thema: {topic}
    Hier sind die aktuellen Daten: {context_data}
    
    Aufgabe:
    1. Fasse die Situation in 2-3 Sätzen zusammen.
    2. Gib eine Einschätzung der Marktstimmung (Bullish/Bearish/Neutral).
    3. Keine Finanzberatung.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Fehler bei der KI-Anfrage: {e}"

# --- DASHBOARD LAYOUT ---
st.title("☕ Dein Daily Dashboard")

col1, col2 = st.columns(2)

# --- PANEL 1: CRYPTO ---
with col1:
    st.subheader("💰 Crypto Analyse")
    btc = yf.Ticker("BTC-EUR")
    hist = btc.history(period="5d")
    
    if not hist.empty:
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change = ((current_price - prev_price) / prev_price) * 100
        
        st.metric("Bitcoin (BTC)", f"{current_price:,.2f} €", f"{change:.2f}%")
        st.line_chart(hist['Close'])
        
        if st.button("KI-Analyse Bitcoin"):
            with st.spinner('Analyst denkt nach...'):
                data_context = f"BTC Preis: {current_price:.2f} EUR. Änderung: {change:.2f}%."
                analysis = get_ai_insight(data_context, "Bitcoin Kursentwicklung")
                st.info(analysis)
    else:
        st.error("Keine Bitcoin-Daten verfügbar.")

# --- PANEL 2: TRENDS ---
with col2:
    st.subheader("🤖 KI Trends")
    # Platzhalter News (später RSS)
    news = [
        "Google Gemini 1.5 Flash ist schneller und günstiger",
        "OpenAI stellt neue Sicherheits-Features vor",
        "Apple integriert KI tiefer in iOS"
    ]
    st.write("Schlagzeilen:")
    for n in news:
        st.text(f"• {n}")
        
    if st.button("KI-Analyse Trends"):
        with st.spinner('Lese News...'):
            analysis = get_ai_insight("\n".join(news), "Aktuelle KI Nachrichten")
            st.success(analysis)
