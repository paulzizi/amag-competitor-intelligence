import gradio as gr
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json
import re
import time
from typing import Dict, List, Tuple
import plotly.graph_objects as go
import plotly.express as px

# Configuration
COMPETITORS = {
    'Emil Frey': {
        'url': 'https://www.emilfrey.ch',
        'aktionen_url': 'https://www.emilfrey.ch/de/aktionen',
        'selector_title': 'h1, h2, h3',
        'selector_price': '.price, .preis, span[class*="price"]'
    },
    'Garage Weiss': {
        'url': 'https://www.garage-weiss.ch',
        'aktionen_url': 'https://www.garage-weiss.ch/angebote',
        'selector_title': 'h1, h2, h3',
        'selector_price': '.price, .preis, span[class*="price"]'
    },
    'Auto Kunz': {
        'url': 'https://www.autokunz.ch',
        'aktionen_url': 'https://www.autokunz.ch/aktionen',
        'selector_title': 'h1, h2, h3',
        'selector_price': '.price, .preis, span[class*="price"]'
    }
}

# Demo/Fallback Data
DEMO_DATA = {
    'Emil Frey': {
        'aktionen': [
            {'title': 'VW Golf - Winteraktion', 'price': 'CHF 29,900', 'discount': '15%'},
            {'title': 'Audi A3 Sportback - Leasing', 'price': 'CHF 299/Mt', 'discount': '0% Leasing'},
            {'title': 'Service-Paket Winter', 'price': 'CHF 199', 'discount': '20% Rabatt'}
        ],
        'keywords': ['winteraktion', 'leasing', 'service', 'vw', 'audi', 'rabatt'],
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    },
    'Garage Weiss': {
        'aktionen': [
            {'title': 'Mercedes A-Klasse', 'price': 'CHF 35,500', 'discount': '10%'},
            {'title': 'BMW 3er - Business Paket', 'price': 'CHF 45,900', 'discount': 'Inkl. Extras'},
            {'title': 'Winterreifen-Aktion', 'price': 'CHF 599', 'discount': '25% Rabatt'}
        ],
        'keywords': ['mercedes', 'bmw', 'business', 'winterreifen', 'premium'],
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    },
    'Auto Kunz': {
        'aktionen': [
            {'title': 'Toyota Hybrid-Wochen', 'price': 'CHF 31,900', 'discount': 'Ökobonus'},
            {'title': 'Mazda CX-5 4x4', 'price': 'CHF 39,900', 'discount': '12%'},
            {'title': 'Gratis-Service 3 Jahre', 'price': 'CHF 0', 'discount': 'Beim Neukauf'}
        ],
        'keywords': ['hybrid', 'toyota', 'mazda', '4x4', 'ökobonus', 'gratis'],
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
}

class CompetitorScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.use_demo_mode = False
        
    def scrape_competitor(self, name: str, config: Dict) -> Dict:
        """Scrape competitor website with fallback to demo data"""
        try:
            # Try actual scraping
            response = requests.get(config['aktionen_url'], headers=self.headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract data
                titles = [t.text.strip() for t in soup.select(config['selector_title'])[:5]]
                prices = [p.text.strip() for p in soup.select(config['selector_price'])[:5]]
                
                # Extract keywords
                text_content = soup.get_text().lower()
                keywords = self.extract_keywords(text_content)
                
                aktionen = []
                for i, title in enumerate(titles):
                    if title:
                        aktionen.append({
                            'title': title,
                            'price': prices[i] if i < len(prices) else 'Auf Anfrage',
                            'discount': self.extract_discount(title + ' ' + (prices[i] if i < len(prices) else ''))
                        })
                
                if aktionen:  # Only return if we found actual data
                    return {
                        'aktionen': aktionen[:3],
                        'keywords': keywords[:10],
                        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'source': 'live'
                    }
        except Exception as e:
            print(f"Scraping failed for {name}: {str(e)}")
        
        # Fallback to demo data
        self.use_demo_mode = True
        demo = DEMO_DATA.get(name, {})
        demo['source'] = 'demo'
        return demo
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        # Common automotive keywords
        auto_keywords = ['leasing', 'rabatt', 'aktion', 'winter', 'sommer', 'service',
                        'garantie', 'finanzierung', 'occasion', 'neuwagen', 'hybrid',
                        'elektro', '4x4', 'suv', 'kombi', 'limousine']
        
        found_keywords = []
        for keyword in auto_keywords:
            if keyword in text:
                found_keywords.append(keyword)
        
        # Extract brand mentions
        brands = ['vw', 'volkswagen', 'audi', 'mercedes', 'bmw', 'toyota', 'mazda',
                 'ford', 'opel', 'seat', 'skoda', 'porsche', 'tesla']
        for brand in brands:
            if brand in text:
                found_keywords.append(brand)
        
        return list(set(found_keywords))[:15]
    
    def extract_discount(self, text: str) -> str:
        """Extract discount information from text"""
        text = text.lower()
        
        # Look for percentage
        percent_match = re.search(r'(\d+)\s*%', text)
        if percent_match:
            return f"{percent_match.group(1)}%"
        
        # Look for CHF amounts
        chf_match = re.search(r'chf\s*(\d+)', text)
        if chf_match:
            return f"CHF {chf_match.group(1)} Rabatt"
        
        # Look for keywords
        if 'gratis' in text:
            return 'Gratis'
        if 'kostenlos' in text:
            return 'Kostenlos'
        if 'aktion' in text:
            return 'Sonderaktion'
        if 'leasing' in text:
            return 'Leasing-Angebot'
        
        return 'Angebot'

class DashboardGenerator:
    def __init__(self):
        self.scraper = CompetitorScraper()
        self.data_cache = {}
        self.last_update = None
        
    def collect_all_data(self) -> Dict:
        """Collect data from all competitors"""
        all_data = {}
        for name, config in COMPETITORS.items():
            all_data[name] = self.scraper.scrape_competitor(name, config)
        
        self.data_cache = all_data
        self.last_update = datetime.now()
        return all_data
    
    def generate_overview_metrics(self, data: Dict) -> pd.DataFrame:
        """Generate overview metrics table"""
        metrics = []
        for competitor, comp_data in data.items():
            metrics.append({
                'Competitor': competitor,
                'Aktive Aktionen': len(comp_data.get('aktionen', [])),
                'Top Keywords': ', '.join(comp_data.get('keywords', [])[:3]),
                'Letzte Aktualisierung': comp_data.get('last_update', 'N/A'),
                'Datenquelle': comp_data.get('source', 'unknown')
            })
        
        return pd.DataFrame(metrics)
    
    def generate_price_comparison(self, data: Dict) -> go.Figure:
        """Generate price comparison chart"""
        fig = go.Figure()
        
        for competitor, comp_data in data.items():
            aktionen = comp_data.get('aktionen', [])
            if aktionen:
                titles = [a['title'][:30] + '...' if len(a['title']) > 30 else a['title'] for a in aktionen]
                prices = []
                for a in aktionen:
                    price_str = a.get('price', '0')
                    # Extract numeric value
                    price_match = re.search(r'(\d+[\'\d]*)', price_str.replace(',', ''))
                    if price_match:
                        prices.append(int(price_match.group(1).replace("'", "")))
                    else:
                        prices.append(0)
                
                fig.add_trace(go.Bar(
                    name=competitor,
                    x=titles,
                    y=prices,
                    text=[a.get('discount', '') for a in aktionen],
                    textposition='auto',
                ))
        
        fig.update_layout(
            title='Aktuelle Aktionen & Preise',
            xaxis_title='Angebote',
            yaxis_title='Preis (CHF)',
            barmode='group',
            height=400,
            showlegend=True
        )
        
        return fig
    
    def generate_keyword_analysis(self, data: Dict) -> go.Figure:
        """Generate keyword frequency analysis"""
        all_keywords = {}
        for competitor, comp_data in data.items():
            for keyword in comp_data.get('keywords', []):
                if keyword not in all_keywords:
                    all_keywords[keyword] = []
                all_keywords[keyword].append(competitor)
        
        # Sort by frequency
        keyword_freq = [(k, len(v)) for k, v in all_keywords.items()]
        keyword_freq.sort(key=lambda x: x[1], reverse=True)
        
        # Create chart
        top_keywords = keyword_freq[:10]
        fig = go.Figure(data=[
            go.Bar(
                x=[k[1] for k in top_keywords],
                y=[k[0] for k in top_keywords],
                orientation='h',
                marker_color='lightblue'
            )
        ])
        
        fig.update_layout(
            title='Top Keywords im Markt',
            xaxis_title='Häufigkeit',
            yaxis_title='Keywords',
            height=400
        )
        
        return fig
    
    def generate_alerts(self, data: Dict) -> List[str]:
        """Generate competitive alerts"""
        alerts = []
        
        for competitor, comp_data in data.items():
            aktionen = comp_data.get('aktionen', [])
            
            # Check for aggressive pricing
            for aktion in aktionen:
                if '20%' in str(aktion.get('discount', '')) or '25%' in str(aktion.get('discount', '')):
                    alerts.append(f"⚠️ {competitor}: Aggressive Rabattaktion - {aktion['title']}")
                
                if 'gratis' in aktion.get('title', '').lower():
                    alerts.append(f"🎁 {competitor}: Gratis-Angebot - {aktion['title']}")
                
                if 'leasing' in aktion.get('title', '').lower():
                    price = aktion.get('price', '')
                    if 'CHF' in price and '/Mt' in price:
                        alerts.append(f"💰 {competitor}: Leasing-Angebot - {aktion['title']}")
        
        # Check for missing keywords (content gaps)
        our_keywords = set(['elektro', 'hybrid', 'online', 'digital'])
        competitor_keywords = set()
        for comp_data in data.values():
            competitor_keywords.update(comp_data.get('keywords', []))
        
        missing_keywords = competitor_keywords - our_keywords
        if missing_keywords:
            alerts.append(f"📊 Content Gap entdeckt: Keywords fehlen: {', '.join(list(missing_keywords)[:3])}")
        
        if not alerts:
            alerts.append("✅ Keine kritischen Wettbewerber-Aktivitäten erkannt")
        
        return alerts[:5]  # Limit to 5 alerts

# Gradio Interface Functions
dashboard_gen = DashboardGenerator()

def refresh_data():
    """Refresh all competitor data"""
    data = dashboard_gen.collect_all_data()
    
    # Generate components
    metrics_df = dashboard_gen.generate_overview_metrics(data)
    price_chart = dashboard_gen.generate_price_comparison(data)
    keyword_chart = dashboard_gen.generate_keyword_analysis(data)
    alerts = dashboard_gen.generate_alerts(data)
    
    # Format alerts
    alerts_html = "<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px;'>"
    for alert in alerts:
        color = '#ff6b6b' if '⚠️' in alert else '#51cf66' if '✅' in alert else '#339af0'
        alerts_html += f"<p style='color: {color}; margin: 5px 0;'>{alert}</p>"
    alerts_html += "</div>"
    
    # Status message
    mode = "Demo-Modus" if dashboard_gen.scraper.use_demo_mode else "Live-Daten"
    status = f"✅ Daten aktualisiert: {datetime.now().strftime('%H:%M:%S')} - {mode}"
    
    return metrics_df, price_chart, keyword_chart, alerts_html, status

def export_data():
    """Export current data as JSON"""
    if dashboard_gen.data_cache:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"competitor_data_{timestamp}.json"
        return json.dumps(dashboard_gen.data_cache, indent=2, ensure_ascii=False)
    return "Keine Daten zum Exportieren vorhanden"

# Create Gradio Interface
with gr.Blocks(title="AMAG Competitor Intelligence", theme=gr.themes.Soft()) as app:
    gr.Markdown("""
    # 🚗 AMAG Competitor Intelligence Dashboard
    **Echtzeit-Monitoring von Emil Frey, Garage Weiss und weiteren Wettbewerbern**
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("### 📊 Dashboard Status")
            status_text = gr.Markdown("Klicken Sie auf 'Daten aktualisieren' um zu starten")
        with gr.Column(scale=1):
            refresh_btn = gr.Button("🔄 Daten aktualisieren", variant="primary")
            export_btn = gr.Button("📥 Daten exportieren")
    
    with gr.Tab("Overview"):
        metrics_table = gr.DataFrame(
            label="Wettbewerber-Übersicht",
            headers=["Competitor", "Aktive Aktionen", "Top Keywords", "Letzte Aktualisierung", "Datenquelle"]
        )
        
    with gr.Tab("Preis-Analyse"):
        price_plot = gr.Plot(label="Aktuelle Aktionen & Preise")
        
    with gr.Tab("Keyword-Analyse"):
        keyword_plot = gr.Plot(label="Keyword-Häufigkeit")
        
    with gr.Tab("Alerts & Insights"):
        alerts_display = gr.HTML(label="Wettbewerber-Alerts")
        gr.Markdown("""
        ### 💡 Empfohlene Aktionen:
        1. **Preisanpassung prüfen** bei aggressiven Wettbewerber-Rabatten
        2. **Content-Gaps schließen** durch fehlende Keywords
        3. **Leasing-Angebote** bei starker Wettbewerber-Aktivität überdenken
        4. **Saisonale Aktionen** rechtzeitig planen (Winter/Sommer)
        """)
    
    with gr.Tab("Export"):
        export_text = gr.Textbox(
            label="JSON Export",
            lines=20,
            max_lines=50,
            placeholder="Klicken Sie auf 'Daten exportieren' um die Daten anzuzeigen"
        )
    
    # Event handlers
    refresh_btn.click(
        fn=refresh_data,
        inputs=[],
        outputs=[metrics_table, price_plot, keyword_plot, alerts_display, status_text]
    )
    
    export_btn.click(
        fn=export_data,
        inputs=[],
        outputs=[export_text]
    )
    
    # Auto-refresh on load
    app.load(
        fn=refresh_data,
        inputs=[],
        outputs=[metrics_table, price_plot, keyword_plot, alerts_display, status_text]
    )

# Launch configuration for Hugging Face Spaces
if __name__ == "__main__":
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )
