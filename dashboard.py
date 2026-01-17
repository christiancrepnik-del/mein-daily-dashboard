import streamlit as st
import yfinance as yf
import google.generativeai as genai
import feedparser
import pandas as pd

# --- KONFIGURATION ---
st.set_page_config(page_title="Morning Briefing", layout="wide")

# Sicherheit: Key aus den Cloud-Secrets holen
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Kein API Key gefunden! Bitte in den Streamlit Secrets eintragen.")
    st.stop()

genai.configure(api_key=API_KEY)

# FIX: Wir nutzen den spezifischen Modell-Namen, um den 404-Fehler zu vermeiden
model = genai.GenerativeModel('gemini-flash-latest')

# --- FUNKTIONEN ---

def calculate_rsi(data, window=14):
    """Berechnet den Relative Strength Index (RSI) für technische Analyse."""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] # Gibt nur den allerneuesten Wert zurück

def get_ai_insight(context_data, topic):
    prompt = f"""
    Du bist ein objektiver Finanz- und Tech-Analyst.
    Thema: {topic}
    Daten: {context_data}
    
    Aufgabe:
    1. Fasse die Situation extrem kurz zusammen.
    2. Wenn es um Finanzen geht: Interpretiere den RSI (Indikator für Überkauft/Überverkauft).
    3. Gib eine klare Einschätzung der Stimmung (Bullish/Bearish/Neutral).
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Fehler bei der KI-Anfrage: {e}"

# --- DASHBOARD LAYOUT ---
st.title("☕ Dein Daily Dashboard")

col1, col2 = st.columns(2)

# --- PANEL 1: CRYPTO MIT RSI ---
with col1:
    st.subheader("💰 Crypto Analyse & Empfehlung")
    
    # Wir holen mehr Daten (1 Monat), damit der RSI berechnet werden kann
    btc = yf.Ticker("BTC-EUR")
    hist = btc.history(period="1mo")
    
    if not hist.empty:
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change = ((current_price - prev_price) / prev_price) * 100
        
        # RSI Berechnung
        current_rsi = calculate_rsi(hist)
        
        # Visuelle Anzeige
        st.metric("Bitcoin (BTC)", f"{current_price:,.2f} €", f"{change:.2f}%")
        
        # RSI Tacho (Simpel dargestellt)
        st.write(f"**RSI Indikator:** {current_rsi:.1f} (0-30: Buy | 70-100: Sell)")
        if current_rsi < 30:
            st.success("Signal: ÜBERVERKAUFT (Mögliche Kauf-Chance)")
        elif current_rsi > 70:
            st.warning("Signal: ÜBERKAUFT (Vorsicht, evtl. Korrektur)")
        else:
            st.info("Signal: NEUTRAL (Halten)")
            
        st.line_chart(hist['Close'])
        
        if st.button("KI-Analyse Bitcoin"):
            with st.spinner('Analyst prüft Indikatoren...'):
                data_context = f"BTC Preis: {current_price:.2f} EUR. RSI: {current_rsi:.1f}."
                analysis = get_ai_insight(data_context, "Bitcoin Kurs & RSI Analyse")
                st.markdown(analysis)

# --- PANEL 2: ECHTE NEWS ---
with col2:
    st.subheader("🤖 Aktuelle Tech-News")
    
    rss_url = "https://www.heise.de/rss/heise-atom.xml" 
    try:
        feed = feedparser.parse(rss_url)
        top_entries = feed.entries[:5]
        news_text = ""
        
        st.caption(f"Quelle: {feed.feed.title}")
        
        for entry in top_entries:
            st.markdown(f"• [{entry.title}]({entry.link})")
            news_text += f"- {entry.title}\n"
            
        if st.button("KI-Analyse der News"):
            with st.spinner('Lese Nachrichten...'):
                analysis = get_ai_insight(news_text, "Aktuelle Tech-Schlagzeilen")
                st.success(analysis)
    except:
        st.error("Konnte News-Feed nicht laden.")

# --- DEBUGGING TOOL (Füg das ganz unten im Code ein) ---
with st.sidebar:
    st.divider()
    st.header("🔧 Diagnose")
    if st.button("Verfügbare Modelle auflisten"):
        try:
            st.write("Frage Google API...")
            models = genai.list_models()
            found_any = False
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    st.code(m.name) # Das hier ist der exakte Name, den wir brauchen
                    found_any = True
            if not found_any:
                st.error("Keine Modelle gefunden! API Key prüfen?")
        except Exception as e:
            st.error(f"Fehler: {e}")
