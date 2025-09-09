"""
AMAG Competitor Intelligence Dashboard
Robust Streamlit Implementation with Fallback Data
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json
import re
import time
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional
import base64
from io import BytesIO

# Page Configuration
st.set_page_config(
    page_title="AMAG Competitor Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {padding-top: 0rem;}
    .stAlert {padding: 1rem; border-radius: 0.5rem;}
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #ddd;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = True

# Configuration
COMPETITORS = {
    'Emil Frey': {
        'url': 'https://www.emilfrey.ch',
        'aktionen_url': 'https://www.emilfrey.ch/de/aktionen',
        'selector_title': 'h1, h2, h3, .title, .headline',
        'selector_price': '.price, .preis, span[class*="price"], .cost'
    },
    'Garage Weiss': {
        'url': 'https://www.garage-weiss.ch',
        'aktionen_url': 'https://www.garage-weiss.ch/angebote',
        'selector_title': 'h1, h2, h3, .title',
        'selector_price': '.price, .preis, span[class*="price"]'
    },
    'Auto Kunz': {
        'url': 'https://www.autokunz.ch',
        'aktionen_url': 'https://www.autokunz.ch/aktionen',
        'selector_title': 'h1, h2, h3',
        'selector_price': '.price, .preis'
    },
    'AMAG': {
        'url': 'https://www.amag.ch',
        'aktionen_url': 'https://www.amag.ch/de/angebote',
        'selector_title': 'h1, h2, h3',
        'selector_price': '.price'
    }
}

# Robust Demo Data
DEMO_DATA = {
    'Emil Frey': {
        'aktionen': [
            {'title': 'VW Golf 8 - Winteraktion 2025', 'price': 'CHF 29,900', 'discount': '15% Rabatt', 'type': 'Neuwagen'},
            {'title': 'Audi A3 Sportback - Top-Leasing', 'price': 'CHF 299/Mt', 'discount': '0% Leasing', 'type': 'Leasing'},
            {'title': 'Service-Paket Winter Komplett', 'price': 'CHF 199', 'discount': '20% Rabatt', 'type': 'Service'},
            {'title': 'Seat Leon FR - Lagerfahrzeug', 'price': 'CHF 26,500', 'discount': '18% Rabatt', 'type': 'Lagerfahrzeug'}
        ],
        'keywords': ['winteraktion', 'leasing', 'service', 'vw', 'audi', 'rabatt', 'seat', 'lagerfahrzeug'],
        'metrics': {'total_offers': 12, 'avg_discount': 15.5, 'new_this_week': 3},
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    },
    'Garage Weiss': {
        'aktionen': [
            {'title': 'Mercedes A-Klasse Edition', 'price': 'CHF 35,500', 'discount': '10% Rabatt', 'type': 'Neuwagen'},
            {'title': 'BMW 3er - Business Paket', 'price': 'CHF 45,900', 'discount': 'Inkl. Extras', 'type': 'Business'},
            {'title': 'Winterreifen-Aktion 2025', 'price': 'CHF 599', 'discount': '25% Rabatt', 'type': 'Reifen'},
            {'title': 'Smart EQ - Elektro-Bonus', 'price': 'CHF 19,900', 'discount': 'Ökoprämie', 'type': 'Elektro'}
        ],
        'keywords': ['mercedes', 'bmw', 'business', 'winterreifen', 'premium', 'elektro', 'smart'],
        'metrics': {'total_offers': 8, 'avg_discount': 12.3, 'new_this_week': 2},
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    },
    'Auto Kunz': {
        'aktionen': [
            {'title': 'Toyota Hybrid-Wochen', 'price': 'CHF 31,900', 'discount': 'Ökobonus CHF 2000', 'type': 'Hybrid'},
            {'title': 'Mazda CX-5 4x4 Revolution', 'price': 'CHF 39,900', 'discount': '12% Rabatt', 'type': 'SUV'},
            {'title': 'Gratis-Service 3 Jahre', 'price': 'CHF 0', 'discount': 'Beim Neukauf', 'type': 'Service'},
            {'title': 'Ford Kuga - Lagerräumung', 'price': 'CHF 28,900', 'discount': '22% Rabatt', 'type': 'Lagerfahrzeug'}
        ],
        'keywords': ['hybrid', 'toyota', 'mazda', '4x4', 'ökobonus', 'gratis', 'ford', 'suv'],
        'metrics': {'total_offers': 10, 'avg_discount': 14.8, 'new_this_week': 4},
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    },
    'AMAG': {
        'aktionen': [
            {'title': 'VW ID.4 - Elektro-Offensive', 'price': 'CHF 42,900', 'discount': 'Inkl. Wallbox', 'type': 'Elektro'},
            {'title': 'Audi Q5 - Premium-Leasing', 'price': 'CHF 599/Mt', 'discount': '1.9% Zins', 'type': 'Leasing'},
            {'title': 'SEAT Ibiza - Young Driver', 'price': 'CHF 18,900', 'discount': '20% Rabatt', 'type': 'Young Driver'},
            {'title': 'Skoda Octavia Combi', 'price': 'CHF 29,900', 'discount': 'CHF 3000 Prämie', 'type': 'Kombi'}
        ],
        'keywords': ['elektro', 'id4', 'premium', 'leasing', 'young', 'skoda', 'vw', 'audi'],
        'metrics': {'total_offers': 15, 'avg_discount': 16.2, 'new_this_week': 5},
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
}

class CompetitorIntelligence:
    """Main scraping and analysis class"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def scrape_competitor(self, name: str, config: Dict) -> Dict:
        """Attempt to scrape, fallback to demo data"""
        try:
            # Attempt real scraping with timeout
            response = requests.get(
                config['aktionen_url'], 
                headers=self.headers, 
                timeout=3,
                verify=False  # In case of SSL issues
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract titles and prices
                titles = []
                prices = []
                
                for selector in config['selector_title'].split(', '):
                    titles.extend([t.text.strip() for t in soup.select(selector)[:3]])
                
                for selector in config['selector_price'].split(', '):
                    prices.extend([p.text.strip() for p in soup.select(selector)[:3]])
                
                if titles:  # Found real data
                    aktionen = []
                    for i, title in enumerate(titles[:4]):
                        aktionen.append({
                            'title': title,
                            'price': prices[i] if i < len(prices) else 'Auf Anfrage',
                            'discount': self._extract_discount(title),
                            'type': 'Live-Daten'
                        })
                    
                    return {
                        'aktionen': aktionen,
                        'keywords': self._extract_keywords(soup.get_text()),
                        'metrics': {'total_offers': len(aktionen), 'avg_discount': 10, 'new_this_week': 1},
                        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'source': 'live'
                    }
        except Exception as e:
            st.session_state.demo_mode = True
            
        # Return demo data as fallback
        return {**DEMO_DATA.get(name, {}), 'source': 'demo'}
    
    def _extract_discount(self, text: str) -> str:
        """Extract discount information"""
        text = text.lower()
        if match := re.search(r'(\d+)\s*%', text):
            return f"{match.group(1)}% Rabatt"
        return "Sonderangebot"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords"""
        keywords = []
        keyword_list = ['leasing', 'rabatt', 'gratis', 'aktion', 'hybrid', 'elektro', 'service']
        for kw in keyword_list:
            if kw in text.lower():
                keywords.append(kw)
        return keywords[:10]

def create_price_comparison_chart(data: Dict) -> go.Figure:
    """Create price comparison visualization"""
    fig = go.Figure()
    
    for competitor, comp_data in data.items():
        aktionen = comp_data.get('aktionen', [])
        if aktionen:
            # Extract numeric prices
            prices = []
            labels = []
            for a in aktionen[:3]:  # Top 3 offers
                price_str = a.get('price', '0')
                if match := re.search(r'(\d+[\'\d]*)', price_str.replace(',', '')):
                    prices.append(int(match.group(1).replace("'", "")))
                    labels.append(a['title'][:20] + '...')
            
            if prices:
                fig.add_trace(go.Bar(
                    name=competitor,
                    x=labels,
                    y=prices,
                    text=[f"{p:,} CHF" for p in prices],
                    textposition='auto',
                ))
    
    fig.update_layout(
        title='Preisvergleich Top-Angebote',
        xaxis_title='Angebote',
        yaxis_title='Preis (CHF)',
        barmode='group',
        height=400,
        template='plotly_white'
    )
    
    return fig

def create_discount_heatmap(data: Dict) -> go.Figure:
    """Create discount heatmap"""
    competitors = list(data.keys())
    categories = ['Neuwagen', 'Leasing', 'Service', 'Elektro']
    
    # Create matrix
    z = []
    for comp in competitors:
        row = []
        for cat in categories:
            # Count offers in category
            count = sum(1 for a in data[comp].get('aktionen', []) 
                       if cat.lower() in str(a.get('type', '')).lower())
            row.append(count)
        z.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=categories,
        y=competitors,
        colorscale='RdYlGn',
        text=z,
        texttemplate="%{text}",
        textfont={"size": 14},
    ))
    
    fig.update_layout(
        title='Angebots-Heatmap nach Kategorie',
        height=350,
        template='plotly_white'
    )
    
    return fig

def generate_competitive_alerts(data: Dict) -> List[Dict]:
    """Generate intelligent alerts"""
    alerts = []
    
    for competitor, comp_data in data.items():
        if competitor == 'AMAG':
            continue
            
        for aktion in comp_data.get('aktionen', []):
            # High discount alerts
            if any(x in str(aktion.get('discount', '')) for x in ['20%', '22%', '25%']):
                alerts.append({
                    'level': 'critical',
                    'icon': '🔴',
                    'message': f"{competitor}: Aggressive Rabattaktion - {aktion['title']} ({aktion['discount']})"
                })
            
            # Leasing alerts
            if 'leasing' in aktion.get('title', '').lower():
                if 'CHF' in aktion.get('price', '') and '/Mt' in aktion.get('price', ''):
                    alerts.append({
                        'level': 'warning',
                        'icon': '🟡',
                        'message': f"{competitor}: Attraktives Leasing - {aktion['price']}"
                    })
            
            # Free service alerts
            if 'gratis' in aktion.get('title', '').lower():
                alerts.append({
                    'level': 'info',
                    'icon': '🔵',
                    'message': f"{competitor}: Gratis-Angebot - {aktion['title']}"
                })
    
    # Content gap analysis
    our_keywords = set(data.get('AMAG', {}).get('keywords', []))
    competitor_keywords = set()
    for comp, comp_data in data.items():
        if comp != 'AMAG':
            competitor_keywords.update(comp_data.get('keywords', []))
    
    missing = competitor_keywords - our_keywords
    if missing:
        alerts.append({
            'level': 'warning',
            'icon': '🟡',
            'message': f"Content Gap: Fehlende Keywords - {', '.join(list(missing)[:3])}"
        })
    
    return alerts[:6]

def export_json_data(data: Dict) -> str:
    """Export data as JSON"""
    export_data = {
        'timestamp': datetime.now().isoformat(),
        'data': data,
        'summary': {
            'total_competitors': len(data),
            'total_offers': sum(len(d.get('aktionen', [])) for d in data.values()),
            'data_source': 'demo' if st.session_state.demo_mode else 'live'
        }
    }
    return json.dumps(export_data, indent=2, ensure_ascii=False)

def main():
    """Main Streamlit application"""
    
    # Header
    col1, col2, col3 = st.columns([2, 3, 1])
    with col1:
        st.title("🚗 AMAG Competitor Intelligence")
    with col2:
        if st.session_state.last_update:
            st.info(f"📊 Update: {st.session_state.last_update}")
    with col3:
        mode_badge = "🔴 Demo-Modus" if st.session_state.demo_mode else "🟢 Live-Daten"
        st.markdown(f"**Status:** {mode_badge}")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Dashboard Control")
        
        if st.button("🔄 Daten aktualisieren", type="primary", use_container_width=True):
            with st.spinner("Lade Daten..."):
                scraper = CompetitorIntelligence()
                data = {}
                for name, config in COMPETITORS.items():
                    data[name] = scraper.scrape_competitor(name, config)
                
                st.session_state.data_cache = data
                st.session_state.last_update = datetime.now().strftime('%H:%M:%S')
                st.rerun()
        
        st.divider()
        
        # Filter options
        st.subheader("🎯 Filter")
        selected_competitors = st.multiselect(
            "Wettbewerber",
            options=list(COMPETITORS.keys()),
            default=list(COMPETITORS.keys())
        )
        
        show_amag = st.checkbox("AMAG-Daten anzeigen", value=True)
        
        st.divider()
        
        # Export section
        st.subheader("📥 Export")
        if st.button("JSON Export", use_container_width=True):
            if st.session_state.data_cache:
                json_data = export_json_data(st.session_state.data_cache)
                st.download_button(
                    label="💾 Download JSON",
                    data=json_data,
                    file_name=f"competitor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    # Initialize with demo data if empty
    if not st.session_state.data_cache:
        st.session_state.data_cache = DEMO_DATA
        st.session_state.last_update = datetime.now().strftime('%H:%M:%S')
    
    # Filter data
    display_data = {k: v for k, v in st.session_state.data_cache.items() 
                    if k in selected_competitors}
    if not show_amag and 'AMAG' in display_data:
        display_data.pop('AMAG')
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "💰 Preisanalyse", 
        "🎯 Alerts & Insights",
        "📈 Keyword-Analyse",
        "📋 Detailansicht"
    ])
    
    with tab1:
        # Key metrics
        st.subheader("Key Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_offers = sum(len(d.get('aktionen', [])) for d in display_data.values())
        avg_discount = sum(d.get('metrics', {}).get('avg_discount', 0) for d in display_data.values()) / max(len(display_data), 1)
        new_offers = sum(d.get('metrics', {}).get('new_this_week', 0) for d in display_data.values())
        
        col1.metric("Total Aktionen", total_offers, delta=f"+{new_offers} neu")
        col2.metric("Ø Rabatt", f"{avg_discount:.1f}%", delta="2.3%")
        col3.metric("Aktive Wettbewerber", len(display_data))
        col4.metric("Keywords erkannt", sum(len(d.get('keywords', [])) for d in display_data.values()))
        
        st.divider()
        
        # Competitor overview table
        st.subheader("Wettbewerber-Übersicht")
        
        overview_data = []
        for comp, data in display_data.items():
            overview_data.append({
                'Wettbewerber': comp,
                'Anzahl Aktionen': len(data.get('aktionen', [])),
                'Top-Angebot': data.get('aktionen', [{}])[0].get('title', 'N/A')[:50] + '...' if data.get('aktionen') else 'N/A',
                'Niedrigster Preis': min([a.get('price', 'N/A') for a in data.get('aktionen', [{'price': 'N/A'}])]),
                'Datenquelle': '🟢 Live' if data.get('source') == 'live' else '🔴 Demo',
                'Update': data.get('last_update', 'N/A')
            })
        
        df = pd.DataFrame(overview_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Preisvergleich & Rabattanalyse")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Price comparison chart
            if display_data:
                fig = create_price_comparison_chart(display_data)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Discount heatmap
            if display_data:
                fig = create_discount_heatmap(display_data)
                st.plotly_chart(fig, use_container_width=True)
        
        # Price table
        st.subheader("Detaillierte Preisübersicht")
        price_data = []
        for comp, data in display_data.items():
            for aktion in data.get('aktionen', []):
                price_data.append({
                    'Wettbewerber': comp,
                    'Angebot': aktion.get('title', 'N/A'),
                    'Preis': aktion.get('price', 'N/A'),
                    'Rabatt': aktion.get('discount', 'N/A'),
                    'Kategorie': aktion.get('type', 'N/A')
                })
        
        if price_data:
            price_df = pd.DataFrame(price_data)
            st.dataframe(price_df, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("🚨 Competitive Alerts & Intelligence")
        
        alerts = generate_competitive_alerts(display_data)
        
        if alerts:
            for alert in alerts:
                if alert['level'] == 'critical':
                    st.error(f"{alert['icon']} {alert['message']}")
                elif alert['level'] == 'warning':
                    st.warning(f"{alert['icon']} {alert['message']}")
                else:
                    st.info(f"{alert['icon']} {alert['message']}")
        else:
            st.success("✅ Keine kritischen Wettbewerber-Aktivitäten erkannt")
        
        st.divider()
        
        # Recommendations
        st.subheader("💡 Handlungsempfehlungen")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Sofort-Massnahmen:**
            1. 🎯 Preisanpassung bei aggressiven Rabatten prüfen
            2. 📝 Content-Gaps in Marketing-Strategie aufnehmen
            3. 💰 Leasing-Konditionen überprüfen
            4. 🚗 Lagerfahrzeuge mit Sonderkonditionen pushen
            """)
        
        with col2:
            st.markdown("""
            **Mittelfristige Strategie:**
            1. 📊 Wöchentliches Monitoring etablieren
            2. 🤝 Kooperationen für bessere Konditionen
            3. 🎨 Unique Selling Points stärken
            4. 📱 Digital-First Ansatz verstärken
            """)
    
    with tab4:
        st.subheader("Keyword & Trend Analyse")
        
        # Collect all keywords
        all_keywords = {}
        for comp, data in display_data.items():
            for kw in data.get('keywords', []):
                if kw not in all_keywords:
                    all_keywords[kw] = []
                all_keywords[kw].append(comp)
        
        if all_keywords:
            # Create keyword frequency chart
            kw_data = pd.DataFrame([
                {'Keyword': kw, 'Häufigkeit': len(comps), 'Wettbewerber': ', '.join(comps)}
                for kw, comps in all_keywords.items()
            ]).sort_values('Häufigkeit', ascending=False)
            
            fig = px.bar(kw_data.head(10), x='Häufigkeit', y='Keyword', 
                        orientation='h', title='Top 10 Keywords im Markt')
            st.plotly_chart(fig, use_container_width=True)
            
            # Keyword table
            st.dataframe(kw_data, use_container_width=True, hide_index=True)
    
    with tab5:
        st.subheader("Detaillierte Wettbewerber-Daten")
        
        # Competitor selector
        selected_comp = st.selectbox("Wettbewerber auswählen", list(display_data.keys()))
        
        if selected_comp and selected_comp in display_data:
            comp_data = display_data[selected_comp]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Anzahl Aktionen", len(comp_data.get('aktionen', [])))
            col2.metric("Ø Rabatt", f"{comp_data.get('metrics', {}).get('avg_discount', 0):.1f}%")
            col3.metric("Neue Angebote", comp_data.get('metrics', {}).get('new_this_week', 0))
            
            # Show all offers
            st.subheader(f"Aktuelle Angebote - {selected_comp}")
            for i, aktion in enumerate(comp_data.get('aktionen', []), 1):
                with st.expander(f"{i}. {aktion.get('title', 'N/A')}"):
                    col1, col2, col3 = st.columns(3)
                    col1.write(f"**Preis:** {aktion.get('price', 'N/A')}")
                    col2.write(f"**Rabatt:** {aktion.get('discount', 'N/A')}")
                    col3.write(f"**Typ:** {aktion.get('type', 'N/A')}")
            
            # Keywords
            if comp_data.get('keywords'):
                st.subheader("Keywords")
                st.write(', '.join([f"`{kw}`" for kw in comp_data.get('keywords', [])]))

if __name__ == "__main__":
    main()
