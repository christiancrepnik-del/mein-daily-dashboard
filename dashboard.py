import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
import time

# --- KONFIGURATION ---
st.set_page_config(page_title="Deep Research Agent", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("API Key fehlt.")
    st.stop()

genai.configure(api_key=API_KEY)
# Wir nutzen 2.5 Flash für Geschwindigkeit und großes Kontext-Fenster
model = genai.GenerativeModel('gemini-2.0-flash')

# --- WERKZEUGE ---

def search_tool(query):
    """Führt eine echte Websuche durch."""
    try:
        results = DDGS().text(query, max_results=3)
        summary = ""
        for r in results:
            summary += f"- {r['title']}: {r['body']} (Link: {r['href']})\n"
        return summary
    except Exception as e:
        return f"Fehler bei der Suche: {e}"

def run_agent_step(history, user_goal):
    """Ein einzelner Denkschritt des Agenten."""
    
    prompt = f"""
    Du bist ein autonomer Research-Agent.
    Ziel des Nutzers: "{user_goal}"
    
    Bisheriger Verlauf:
    {history}
    
    Deine Anweisungen:
    1. Analysiere, welche Informationen dir noch fehlen, um das Ziel perfekt zu beantworten.
    2. Wenn du Informationen brauchst, antworte EXAKT im Format: 
       SEARCH: [Deine Suchanfrage]
    3. Wenn du genug Informationen hast, antworte EXAKT im Format:
       ANSWER: [Deine ausführliche, finale Antwort mit Quellen]
       
    Wichtig: Mache immer nur EINEN Schritt (Suchen ODER Antworten).
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

# --- UI ---

st.title("🕵️‍♂️ Deep Research Agent")
st.markdown("Dieser Agent denkt selbstständig nach und führt mehrere Suchschritte aus, um eine komplexe Frage zu beantworten.")

# Eingabe
user_query = st.text_input("Was soll ich recherchieren?", "Wie steht es aktuell um Bitcoin und gibt es wichtige regulatorische News?")
start_btn = st.button("🚀 Deep Research starten", type="primary")

# Der Agenten-Loop
if start_btn and user_query:
    history = ""
    step_count = 0
    max_steps = 5 
    
    status_container = st.container()
    
    with status_container:
        st.write("---")
        progress_log = st.empty()
        
        while step_count < max_steps:
            step_count += 1
            
            # WICHTIG: Atempause vor jeder KI-Anfrage, um "ResourceExhausted" zu vermeiden
            if step_count > 1:
                time.sleep(5) # 5 Sekunden Pause zwischen den Gedanken
            
            try:
                # 1. Agenten fragen (Denken)
                with st.spinner(f"Schritt {step_count}: Agent denkt nach..."):
                    response = run_agent_step(history, user_query)
                
                # 2. Entscheidung: Suchen oder Antworten?
                if response.startswith("SEARCH:"):
                    query = response.replace("SEARCH:", "").strip()
                    st.info(f"🔍 **Agent sucht:** '{query}'")
                    
                    search_results = search_tool(query)
                    
                    history += f"\n--- SCHRITT {step_count} ---\n"
                    history += f"AGENT ACTION: Search for '{query}'\n"
                    history += f"SEARCH RESULTS: {search_results}\n"
                    
                elif response.startswith("ANSWER:"):
                    final_answer = response.replace("ANSWER:", "").strip()
                    st.success("✅ Recherche abgeschlossen!")
                    st.markdown("### 📝 Ergebnisbericht")
                    st.markdown(final_answer)
                    break # Schleife beenden
                
                else:
                    st.warning(f"Unerwartete Antwort: {response}")
                    history += f"\n(Fehler: Bitte nutze SEARCH: oder ANSWER:)\n"
            
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten (meistens Limit erreicht): {e}")
                st.warning("Tipp: Warte eine Minute und versuche es erneut.")
                break # Notbremse
        
        # Falls die Schritte aufgebraucht sind oder ein Fehler passierte
        if step_count >= max_steps:
            st.warning("Maximale Schritte erreicht. Erstelle Zusammenfassung des bisherigen Wissens...")
            try:
                time.sleep(2) # Kurze Pause vor dem letzten Call
                final = model.generate_content(f"Fasse zusammen was wir bisher wissen zu: {user_query}. Verlauf: {history}")
                st.markdown(final.text)
            except Exception as e:
                st.error("Konnte keine Zusammenfassung erstellen (Limit erreicht).")
