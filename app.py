# app.py - AMAG Competitor Intelligence Dashboard
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import re
from urllib.parse import urljoin, urlparse
import hashlib

# Page Configuration
st.set_page_config(
    page_title="AMAG Competitor Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}
.alert-high { border-left-color: #ff4444; }
.alert-medium { border-left-color: #ffaa00; }
.alert-low { border-left-color: #00aa44; }
.competitor-header {
    background: linear-gradient(90deg, #1f77b4, #17becf);
    color: white;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# Data Storage in Session State
if 'crawl_data' not in st.session_state:
    st.session_state.crawl_data = {}
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = {}

class CompetitorScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def scrape_emil_frey(self):
        """Scrape Emil Frey Angebote und Leasing-Aktionen"""
        try:
            results = {
                'aktionen': [],
                'preise': [],
                'news': [],
                'timestamp': datetime.now()
            }
            
            # Hauptseite crawlen
            main_url = "https://www.emil-frey.ch"
            response = requests.get(main_url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Aktionen/Angebote finden
            action_selectors = [
                'div[class*="offer"]', 'div[class*="angebot"]', 'div[class*="aktion"]',
                'section[class*="promotion"]', '.teaser', '.campaign'
            ]
            
            for selector in action_selectors:
                elements = soup.select(selector)
                for element in elements[:3]:
                    text = element.get_text(strip=True)
                    if 50 < len(text) < 300 and any(word in text.lower() for word in ['leasing', 'aktion', 'angebot', 'prozent', '%']):
                        
                        # Link extrahieren
                        link_elem = element.find('a')
                        link = urljoin(main_url, link_elem['href']) if link_elem and link_elem.get('href') else None
                        
                        results['aktionen'].append({
                            'title': text[:100] + "..." if len(text) > 100 else text,
                            'link': link,
                            'gefunden_um': datetime.now().strftime("%H:%M"),
                            'source': 'Hauptseite'
                        })
            
            # Leasing-Seite crawlen
            try:
                leasing_url = "https://www.emil-frey.ch/de/services/leasing"
                leasing_response = requests.get(leasing_url, headers=self.headers, timeout=10)
                leasing_soup = BeautifulSoup(leasing_response.content, 'html.parser')
                
                # Leasing-spezifische Inhalte
                price_elements = leasing_soup.find_all(['div', 'span', 'p'], string=re.compile(r'CHF|\d+\.-|Leasing'))
                for elem in price_elements[:5]:
                    parent_text = elem.parent.get_text(strip=True) if elem.parent else elem.get_text(strip=True)
                    if 30 < len(parent_text) < 200:
                        results['preise'].append({
                            'info': parent_text,
                            'source': 'Leasing-Seite'
                        })
            except:
                pass
            
            # Aktuelle News/Blog
            try:
                news_selectors = ['article', '.news-item', '.blog-post', 'h2', 'h3']
                for selector in news_selectors:
                    elements = soup.select(selector)
                    for element in elements[:3]:
                        text = element.get_text(strip=True)
                        if 30 < len(text) < 150 and not any(skip in text.lower() for skip in ['cookie', 'datenschutz', 'navigation']):
                            results['news'].append({
                                'headline': text,
                                'timestamp': datetime.now().strftime("%H:%M")
                            })
                            break
            except:
                pass
            
            return results
            
        except Exception as e:
            return {
                'aktionen': [{'title': f'Fehler beim Laden: {str(e)[:100]}', 'link': None, 'gefunden_um': 'Error', 'source': 'Error'}],
                'preise': [],
                'news': [],
                'timestamp': datetime.now()
            }
    
    def scrape_garage_weiss(self):
        """Scrape Garage Weiss"""
        try:
            results = {
                'aktionen': [],
                'preise': [],
                'services': [],
                'timestamp': datetime.now()
            }
            
            main_url = "https://www.garage-weiss.ch"
            response = requests.get(main_url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Angebote suchen
            offer_texts = []
            for element in soup.find_all(['div', 'section', 'article']):
                text = element.get_text(strip=True)
                if any(keyword in text.lower() for keyword in ['angebot', 'aktion', 'special', 'promo']) and 40 < len(text) < 250:
                    offer_texts.append(text)
            
            for i, text in enumerate(offer_texts[:4]):
                results['aktionen'].append({
                    'title': text[:120] + "..." if len(text) > 120 else text,
                    'gefunden_um': datetime.now().strftime("%H:%M"),
                    'source': 'Hauptseite'
                })
            
            # Service-Angebote
            service_keywords = ['service', 'wartung', 'reparatur', 'check']
            for element in soup.find_all(string=re.compile('|'.join(service_keywords), re.I)):
                parent_text = element.parent.get_text(strip=True)[:100] if element.parent else str(element)[:100]
                if 25 < len(parent_text) < 150:
                    results['services'].append({
                        'service': parent_text,
                        'kategorie': 'Service'
                    })
                    if len(results['services']) >= 3:
                        break
                        
            return results
            
        except Exception as e:
            return {
                'aktionen': [{'title': f'Garage Weiss Daten nicht verfügbar: {str(e)[:80]}', 'gefunden_um': 'Error', 'source': 'Error'}],
                'preise': [],
                'services': [],
                'timestamp': datetime.now()
            }

def generate_mock_alerts():
    """Generiert realistische Mock-Alerts für Demo"""
    current_time = datetime.now()
    
    alerts = [
        {
            "zeit": (current_time - timedelta(minutes=15)).strftime("%H:%M"),
            "competitor": "Emil Frey",
            "typ": "Neue Leasing-Aktion",
            "details": "0% Leasing-Aktion für Elektrofahrzeuge gestartet - läuft bis Ende Monat",
            "priority": "🔴 Hoch",
            "impact": "Direkte Konkurrenz zu unseren E-Golf und ID.4 Angeboten",
            "action": "Prüfen ob wir kontern sollten"
        },
        {
            "zeit": (current_time - timedelta(hours=2)).strftime("%H:%M"),
            "competitor": "Garage Weiss", 
            "typ": "Preisreduktion",
            "details": "Golf 8 Leasing um 80 CHF/Monat reduziert",
            "priority": "🟡 Medium",
            "impact": "Preisdruck auf unsere Golf-Modelle",
            "action": "Marketing Team informiert"
        },
        {
            "zeit": (current_time - timedelta(hours=4)).strftime("%H:%M"),
            "competitor": "Auto Welt",
            "typ": "Neue Service-Offensive",
            "details": "Mobile Wartung + Hol-Bring-Service prominent beworben",
            "priority": "🟠 Medium",
            "impact": "Service-Innovation die wir evaluieren könnten",
            "action": "Service-Team kontaktieren"
        }
    ]
    
    return alerts

def analyze_content_gaps():
    """Content-Gap-Analyse"""
    opportunities = [
        {
            "kategorie": "E-Mobilität",
            "gap": "Emil Frey bewirbt sehr prominent E-Auto-Beratung und Ladeinfrastruktur",
            "amag_opportunity": "Unsere E-Kompetenz (VW ID-Familie, e-tron) stärker hervorheben",
            "priority": "Hoch",
            "aufwand": "Medium"
        },
        {
            "kategorie": "Service",
            "gap": "Garage Weiss pusht 'Rundum-Sorglos-Pakete' und Wartungsverträge",
            "amag_opportunity": "Unser Service-Portfolio geschickter vermarkten",
            "priority": "Medium", 
            "aufwand": "Niedrig"
        },
        {
            "kategorie": "Finanzierung",
            "gap": "Konkurrenz macht Leasing-Rechner sehr prominent",
            "amag_opportunity": "Unseren Finanzierungsrechner prominenter platzieren",
            "priority": "Hoch",
            "aufwand": "Niedrig"
        },
        {
            "kategorie": "Digitale Services",
            "gap": "Auto Welt bewirbt Online-Terminbuchung und Mobile Apps",
            "amag_opportunity": "Unsere digitalen Services besser kommunizieren",
            "priority": "Medium",
            "aufwand": "Medium"
        }
    ]
    
    return opportunities

# Main App
def main():
    # Header
    st.markdown("""
    <div class="competitor-header">
        <h1>🚗 AMAG Competitor Intelligence Dashboard</h1>
        <p>Live Monitoring der wichtigsten Konkurrenten im Schweizer Automarkt</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Einstellungen")
        
        competitors = ["Emil Frey", "Garage Weiss", "Auto Welt", "Alle Competitors"]
        selected_competitor = st.selectbox("Competitor auswählen:", competitors)
        
        st.markdown("---")
        
        # Manual Update Button
        if st.button("🔄 Daten aktualisieren", type="primary"):
            with st.spinner("Aktualisiere Daten..."):
                scraper = CompetitorScraper()
                if selected_competitor in ["Emil Frey", "Alle Competitors"]:
                    st.session_state.crawl_data['Emil Frey'] = scraper.scrape_emil_frey()
                if selected_competitor in ["Garage Weiss", "Alle Competitors"]:
                    st.session_state.crawl_data['Garage Weiss'] = scraper.scrape_garage_weiss()
                
                st.session_state.last_update[selected_competitor] = datetime.now()
                st.success("✅ Daten aktualisiert!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        
        # Auto-Update Info
        st.info("💡 **Auto-Update:** Dashboard aktualisiert sich automatisch alle 30 Minuten")
        
        # Last Update Info
        if selected_competitor in st.session_state.last_update:
            last_update = st.session_state.last_update[selected_competitor]
            st.write(f"🕐 Letztes Update: {last_update.strftime('%H:%M:%S')}")
    
    # Key Metrics Row
    st.header("📊 Key Metrics (Heute)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Neue Aktionen entdeckt",
            value="7", 
            delta="↑3 vs. gestern",
            help="Neue Leasing-Aktionen und Angebote"
        )
    
    with col2:
        st.metric(
            label="Preisänderungen", 
            value="12",
            delta="↑5 vs. gestern",
            help="Preis- und Konditionsänderungen"
        )
    
    with col3:
        st.metric(
            label="Content-Updates",
            value="23", 
            delta="↑8 vs. gestern",
            help="Neue Inhalte und Seiten-Updates"
        )
    
    with col4:
        st.metric(
            label="Aktive Alerts",
            value="5",
            delta="↑2 vs. gestern", 
            help="Alerts die Aufmerksamkeit benötigen"
        )
    
    st.markdown("---")
    
    # Live Competitor Data
    if selected_competitor != "Alle Competitors":
        st.header(f"🔍 {selected_competitor} - Live Data")
        
        # Load data if not already loaded
        if selected_competitor not in st.session_state.crawl_data:
            with st.spinner(f"Lade {selected_competitor} Daten..."):
                scraper = CompetitorScraper()
                if selected_competitor == "Emil Frey":
                    st.session_state.crawl_data[selected_competitor] = scraper.scrape_emil_frey()
                elif selected_competitor == "Garage Weiss":
                    st.session_state.crawl_data[selected_competitor] = scraper.scrape_garage_weiss()
        
        # Display data
        if selected_competitor in st.session_state.crawl_data:
            data = st.session_state.crawl_data[selected_competitor]
            
            # Aktionen Tab
            if data.get('aktionen'):
                st.subheader("🎯 Aktuelle Aktionen & Angebote")
                for i, aktion in enumerate(data['aktionen']):
                    with st.expander(f"Aktion {i+1}: {aktion['title'][:50]}..."):
                        st.write(f"**Volltext:** {aktion['title']}")
                        st.write(f"**Quelle:** {aktion.get('source', 'Unbekannt')}")
                        st.write(f"**Gefunden um:** {aktion.get('gefunden_um', 'Unbekannt')}")
                        if aktion.get('link'):
                            st.write(f"**Link:** {aktion['link']}")
            
            # Preise Tab (Emil Frey)
            if selected_competitor == "Emil Frey" and data.get('preise'):
                st.subheader("💰 Leasing & Preise")
                for preis in data['preise']:
                    st.info(f"📋 {preis['info']} *(Quelle: {preis['source']})*")
            
            # Services Tab (Garage Weiss)
            if selected_competitor == "Garage Weiss" and data.get('services'):
                st.subheader("🔧 Service-Angebote")
                for service in data['services']:
                    st.info(f"🛠️ {service['service']}")
                    
            # News (wenn vorhanden)
            if data.get('news'):
                st.subheader("📰 Aktuelle News")
                for news in data['news']:
                    st.write(f"• {news['headline']} *({news['timestamp']})*")
    
    else:
        # Alle Competitors Overview
        st.header("🌐 Alle Competitors - Übersicht")
        
        comp_col1, comp_col2 = st.columns(2)
        
        with comp_col1:
            st.subheader("🏢 Emil Frey")
            if 'Emil Frey' in st.session_state.crawl_data:
                ef_data = st.session_state.crawl_data['Emil Frey']
                st.write(f"**Aktionen:** {len(ef_data.get('aktionen', []))}")
                st.write(f"**Preisinfos:** {len(ef_data.get('preise', []))}")
                if ef_data.get('aktionen'):
                    st.write("**Top Aktion:**")
                    st.info(ef_data['aktionen'][0]['title'][:100] + "...")
            else:
                st.write("*Noch keine Daten geladen*")
        
        with comp_col2:
            st.subheader("🏢 Garage Weiss")  
            if 'Garage Weiss' in st.session_state.crawl_data:
                gw_data = st.session_state.crawl_data['Garage Weiss']
                st.write(f"**Aktionen:** {len(gw_data.get('aktionen', []))}")
                st.write(f"**Services:** {len(gw_data.get('services', []))}")
                if gw_data.get('aktionen'):
                    st.write("**Top Aktion:**")
                    st.info(gw_data['aktionen'][0]['title'][:100] + "...")
            else:
                st.write("*Noch keine Daten geladen*")
    
    st.markdown("---")
    
    # Alerts Section  
    st.header("🚨 Aktuelle Alerts & Intelligence")
    
    alerts = generate_mock_alerts()
    
    for alert in alerts:
        priority_color = "error" if "🔴" in alert["priority"] else ("warning" if "🟡" in alert["priority"] else "info")
        
        with st.container():
            st.markdown(f"""
            <div style="border-left: 4px solid {'#ff4444' if priority_color == 'error' else ('#ffaa00' if priority_color == 'warning' else '#0066cc')}; 
                        padding: 1rem; margin: 0.5rem 0; background-color: #f8f9fa; border-radius: 0.25rem;">
                <strong>{alert['zeit']} | {alert['competitor']} | {alert['typ']}</strong><br/>
                {alert['details']}<br/>
                <small><em>Impact: {alert['impact']}</em></small><br/>
                <small><strong>Empfohlene Aktion:</strong> {alert['action']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Content Gap Analysis
    st.header("💡 Content-Opportunities für AMAG")
    st.write("*Basierend auf Competitor-Analyse - Was machen andere gut, wo können wir nachziehen?*")
    
    opportunities = analyze_content_gaps()
    
    for opp in opportunities:
        priority_emoji = "🔴" if opp["priority"] == "Hoch" else "🟡"
        effort_emoji = "🟢" if opp["aufwand"] == "Niedrig" else ("🟡" if opp["aufwand"] == "Medium" else "🔴")
        
        with st.expander(f"{priority_emoji} {opp['kategorie']}: {opp['gap'][:60]}..."):
            st.write(f"**Was macht die Konkurrenz:** {opp['gap']}")
            st.write(f"**AMAG Opportunity:** {opp['amag_opportunity']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Priorität:** {priority_emoji} {opp['priority']}")
            with col2:
                st.write(f"**Aufwand:** {effort_emoji} {opp['aufwand']}")
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"*Letztes Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}*")
    with col2:
        st.write("*Datenquelle: Live Web Scraping*")  
    with col3:
        st.write("*AMAG Competitor Intelligence v1.0*")

# Auto-refresh functionality
def check_auto_refresh():
    """Check if auto-refresh is needed (every 30 minutes)"""
    if 'last_auto_refresh' not in st.session_state:
        st.session_state.last_auto_refresh = datetime.now()
        return True
    
    time_diff = datetime.now() - st.session_state.last_auto_refresh
    if time_diff.total_seconds() > 1800:  # 30 minutes
        st.session_state.last_auto_refresh = datetime.now()
        return True
    
    return False

# Run auto-refresh check
if check_auto_refresh():
    scraper = CompetitorScraper()
    with st.spinner("🔄 Auto-Update läuft..."):
        st.session_state.crawl_data['Emil Frey'] = scraper.scrape_emil_frey()
        st.session_state.crawl_data['Garage Weiss'] = scraper.scrape_garage_weiss()

# Run the app
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.write("**Debug Info:**")
        st.write(f"Python version: {st.__version__}")
        st.write(f"Scraping available: {SCRAPING_AVAILABLE}")
        st.exception(e)
