import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import io
from functools import lru_cache
import warnings
warnings.filterwarnings("ignore")

# ============================================================================
# CONFIGURATION STREAMLIT
# ============================================================================
st.set_page_config(
    page_title="Alpha Terminal Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS PERSONNALISÉ - Dark Mode Premium
st.markdown("""
<style>
:root {
    --primary-color: #1f77b4;
    --secondary-color: #ff7f0e;
    --success-color: #2ca02c;
    --danger-color: #d62728;
    --bg-dark: #0e1117;
    --card-bg: #161b22;
    --border-color: #30363d;
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
}

* {
    color: var(--text-primary) !important;
}

.metric-card {
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px 20px;
    margin: 8px 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    font-weight: 500;
}

.score-good { color: var(--success-color) !important; }
.score-warn { color: var(--secondary-color) !important; }
.score-bad { color: var(--danger-color) !important; }

.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin: 16px 0;
}

.title-section {
    border-left: 4px solid var(--primary-color);
    padding-left: 12px;
    margin: 20px 0 12px 0;
}

.stTabs [data-baseweb="tab-list"] button { font-weight: 600; }
.stMetricDelta { color: var(--text-secondary) !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FONCTIONS UTILITAIRES - PARSING DÉFENSIF
# ============================================================================

@lru_cache(maxsize=128)
def get_currency_to_eur_rate(currency_code: str) -> float:
    """
    Récupère le taux de change vers EUR avec fallbacks pour fiabilité.
    """
    if currency_code == "EUR":
        return 1.0
    
    fallback_rates = {
        "USD": 0.92,
        "GBP": 1.17,
        "CHF": 1.04,
        "CAD": 0.68,
        "JPY": 0.0067,
        "AUD": 0.61,
        "CNY": 0.128,
        "INR": 0.011,
    }
    
    try:
        ticker = yf.Ticker(f"{currency_code}EUR=X")
        rate = ticker.info.get("currentPrice", fallback_rates.get(currency_code, 1.0))
        return float(rate) if rate else fallback_rates.get(currency_code, 1.0)
    except:
        return fallback_rates.get(currency_code, 1.0)

def safe_float(value, default: float = None) -> float | None:
    """Parse défensif float avec gestion erreurs."""
    try:
        if value is None or value == "N/A":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def safe_pct(value, decimal: int = 2) -> str:
    """Formate pourcentage avec fallback."""
    try:
        num = safe_float(value)
        return f"{num:.{decimal}f}%" if num is not None else "N/A"
    except:
        return "N/A"

def safe_str(value) -> str:
    """Parse défensif string."""
    try:
        return str(value) if value else "N/A"
    except:
        return "N/A"

def format_large_number(num) -> str:
    """Formate grands nombres (K, M, B, T)."""
    try:
        num = float(num)
        if num >= 1e12:
            return f"{num/1e12:.2f}T"
        elif num >= 1e9:
            return f"{num/1e9:.2f}B"
        elif num >= 1e6:
            return f"{num/1e6:.2f}M"
        elif num >= 1e3:
            return f"{num/1e3:.2f}K"
        else:
            return f"{num:.2f}"
    except:
        return "N/A"

# ============================================================================
# FONCTION PRINCIPALE - RÉCUPÉRATION DES DONNÉES
# ============================================================================

def fetch_ticker_data(ticker_symbol: str):
    """Récupère et traite données complètes du ticker."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Données basiques
        info = ticker.info or {}
        currency = info.get("currency", "USD")
        eur_rate = get_currency_to_eur_rate(currency)
        
        # Détection ETF
        is_etf = info.get("quoteType") == "ETF" or "ETF" in info.get("longName", "")
        
        return {
            "ticker": ticker,
            "symbol": ticker_symbol,
            "info": info,
            "currency": currency,
            "eur_rate": eur_rate,
            "is_etf": is_etf,
            "hist": ticker.history(period="5y"),
            "error": None
        }
    except Exception as e:
        return {
            "ticker": None,
            "symbol": ticker_symbol,
            "info": {},
            "currency": "USD",
            "eur_rate": 1.0,
            "is_etf": False,
            "hist": None,
            "error": str(e)
        }

# ============================================================================
# MODULE 1 : CALCUL DES 21 RATIOS
# ============================================================================

def calculate_valuation_metrics(data: dict) -> dict:
    """Calcule 8 ratios de valorisation & prix."""
    info = data["info"]
    eur_rate = data["eur_rate"]
    
    # 1. PER Actuel (Trailing)
    per_trailing = safe_float(info.get("trailingPE"))
    
    # 2. PER Futur (Forward)
    per_forward = safe_float(info.get("forwardPE"))
    
    # 3. P/S Ratio
    ps_ratio = safe_float(info.get("priceToSalesTrailing12Months"))
    
    # 4. P/B Ratio
    pb_ratio = safe_float(info.get("priceToBook"))
    
    # 5. EV/EBITDA
    ev_ebitda = safe_float(info.get("enterpriseToEbitda"))
    
    # 6. BPA (EPS) en EUR
    eps = safe_float(info.get("trailingEps"))
    eps_eur = (eps * eur_rate) if eps else None
    
    # 7. Valeur Comptable par Action en EUR
    book_value = safe_float(info.get("bookValue"))
    book_value_eur = (book_value * eur_rate) if book_value else None
    
    # 8. Prix Théorique Graham
    graham_price = None
    if eps and book_value:
        try:
            product = 22.5 * abs(eps) * abs(book_value)
            graham_price = np.sqrt(product) * eur_rate if product > 0 else None
        except:
            graham_price = None
    
    return {
        "per_trailing": per_trailing,
        "per_forward": per_forward,
        "ps_ratio": ps_ratio,
        "pb_ratio": pb_ratio,
        "ev_ebitda": ev_ebitda,
        "eps_eur": eps_eur,
        "book_value_eur": book_value_eur,
        "graham_price": graham_price,
    }

def calculate_profitability_metrics(data: dict) -> dict:
    """Calcule 5 ratios de rentabilité."""
    info = data["info"]
    
    return {
        "gross_margin": safe_float(info.get("grossMargins")),
        "operating_margin": safe_float(info.get("operatingMargins")),
        "profit_margin": safe_float(info.get("profitMargins")),
        "roe": safe_float(info.get("returnOnEquity")),
        "roa": safe_float(info.get("returnOnAssets")),
    }

def calculate_financial_health(data: dict) -> dict:
    """Calcule 6 ratios de santé financière & bilan."""
    info = data["info"]
    eur_rate = data["eur_rate"]
    
    # 14. Dette Nette en M€
    total_debt = safe_float(info.get("totalDebt", 0))
    cash = safe_float(info.get("totalCash", 0))
    net_debt = (total_debt - cash) * eur_rate / 1e6 if total_debt else None
    
    # 15. EBITDA en M€
    ebitda = safe_float(info.get("ebitda"))
    ebitda_millions = (ebitda * eur_rate / 1e6) if ebitda else None
    
    # 16. Ratio Dette Nette / EBITDA
    net_debt_ebitda = None
    if net_debt is not None and ebitda_millions and ebitda_millions > 0:
        if net_debt < 0:
            net_debt_ebitda = "Cash Positif"
        else:
            net_debt_ebitda = net_debt / ebitda_millions
    
    # 17. Current Ratio
    current_ratio = safe_float(info.get("currentRatio"))
    
    # 18. Quick Ratio
    quick_ratio = safe_float(info.get("quickRatio"))
    
    # 19. Debt to Equity
    de_ratio = safe_float(info.get("debtToEquity"))
    de_percent = (de_ratio * 100) if de_ratio else None
    
    return {
        "net_debt_millions": net_debt,
        "ebitda_millions": ebitda_millions,
        "net_debt_ebitda": net_debt_ebitda,
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "debt_to_equity_pct": de_percent,
    }

def calculate_growth_metrics(data: dict) -> dict:
    """Calcule 2 ratios de croissance & dividendes."""
    info = data["info"]
    
    # 20. Revenue Growth
    revenue_growth = safe_float(info.get("revenueGrowth"))
    
    # 21. Payout Ratio
    payout_ratio = safe_float(info.get("payoutRatio"))
    
    return {
        "revenue_growth": revenue_growth,
        "payout_ratio": payout_ratio,
    }

def calculate_fundamental_score(data: dict, valuation: dict, profitability: dict, 
                                 health: dict, growth: dict) -> dict:
    """Calcule Score Fondamental 0-100 avec règles strictes."""
    score = 50  # Base neutre
    info = data["info"]
    
    # Règles de scoring
    try:
        # Valorisation (25 points max)
        if valuation["per_trailing"] and valuation["per_trailing"] < 20:
            score += 8
        if valuation["pb_ratio"] and valuation["pb_ratio"] < 3:
            score += 8
        if valuation["graham_price"] and valuation["graham_price"] > info.get("currentPrice", 0):
            score += 9
        
        # Rentabilité (25 points max)
        if profitability["profit_margin"] and profitability["profit_margin"] > 0.12:
            score += 10
        if profitability["roe"] and profitability["roe"] > 0.15:
            score += 8
        if profitability["roa"] and profitability["roa"] > 0.08:
            score += 7
        
        # Santé (30 points max)
        if isinstance(health["net_debt_ebitda"], (int, float)) and health["net_debt_ebitda"] < 2:
            score += 12
        elif health["net_debt_ebitda"] == "Cash Positif":
            score += 15
        if health["current_ratio"] and 1.5 < health["current_ratio"] < 3:
            score += 8
        if health["debt_to_equity_pct"] and health["debt_to_equity_pct"] < 100:
            score += 10
        
        # Croissance (20 points max)
        if growth["revenue_growth"] and growth["revenue_growth"] > 0.1:
            score += 12
        if growth["payout_ratio"] and 0.2 < growth["payout_ratio"] < 0.7:
            score += 8
        
    except:
        pass
    
    score = min(100, max(0, score))
    
    # Couleur
    if score >= 75:
        color = "🟢"
    elif score >= 50:
        color = "🟡"
    else:
        color = "🔴"
    
    return {
        "score": score,
        "color": color,
        "level": "Excellent" if score >= 75 else "Bon" if score >= 50 else "À surveiller"
    }

# ============================================================================
# MODULE 2 : ANALYSE ETF
# ============================================================================

def analyze_etf(data: dict) -> dict:
    """Analyse complète d'un ETF."""
    info = data["info"]
    
    ter = safe_float(info.get("expense_ratio")) or safe_float(info.get("fundExpenseRatio"))
    aum = safe_float(info.get("totalAssets"))
    aum_millions = (aum * data["eur_rate"] / 1e6) if aum else None
    
    # Détection distribution
    distribution = "Capitalisation"
    if any(x in data["symbol"].upper() for x in ["DIST", "D", "UCITS"]):
        distribution = "Distributif"
    
    # Éligibilité PEA (heuristique)
    pea_eligible = "Non spécifié"
    if any(x in info.get("longName", "").upper() for x in ["MSCI WORLD", "STOXX 600", "CAC 40", "EURO"]):
        if ".PA" in data["symbol"] or info.get("exchange") == "PAR":
            pea_eligible = "Probable (PEA)"
    
    return {
        "ter": ter,
        "aum_millions": aum_millions,
        "distribution": distribution,
        "pea_eligible": pea_eligible,
        "low_aum_alert": aum_millions and aum_millions < 100,
    }

# ============================================================================
# MODULE 4 : SIMULATEUR DCA
# ============================================================================

def simulate_dca(ticker_data: dict, monthly_amount: float, years_back: int) -> dict:
    """Simule stratégie Dollar Cost Averaging avec données réelles."""
    if ticker_data["hist"] is None or len(ticker_data["hist"]) == 0:
        return {"error": "Pas de données historiques disponibles"}
    
    try:
        hist = ticker_data["hist"].sort_index()
        start_date = datetime.now() - timedelta(days=365 * years_back)
        hist = hist[hist.index >= start_date].copy()
        
        if len(hist) == 0:
            return {"error": "Pas de données pour la période sélectionnée"}
        
        # Simul DCA : achats 1er jour ouvré de chaque mois
        purchase_dates = []
        current_month = None
        
        for date in hist.index:
            if current_month != date.month:
                purchase_dates.append(date)
                current_month = date.month
        
        # Calculs
        shares = 0
        total_invested = 0
        portfolio_value = []
        invested_value = []
        timeline_dates = []
        
        for purchase_date in purchase_dates:
            price = hist.loc[purchase_date, "Close"]
            shares += monthly_amount / price
            total_invested += monthly_amount
            
            current_price = hist.iloc[-1]["Close"]
            current_value = shares * current_price
            
            portfolio_value.append(current_value)
            invested_value.append(total_invested)
            timeline_dates.append(purchase_date)
        
        final_value = portfolio_value[-1] if portfolio_value else 0
        gain = final_value - total_invested
        gain_pct = (gain / total_invested * 100) if total_invested > 0 else 0
        
        return {
            "timeline": timeline_dates,
            "invested": invested_value,
            "portfolio": portfolio_value,
            "total_invested": total_invested,
            "final_value": final_value,
            "gain": gain,
            "gain_pct": gain_pct,
            "shares": shares,
            "error": None
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# MODULE 5 : NEWS FIABLE
# ============================================================================

def get_ticker_news(ticker_data: dict, limit: int = 5) -> list:
    """Récupère actualités de manière sécurisée."""
    try:
        news = ticker_data["ticker"].news[:limit] if ticker_data["ticker"] else []
        return news or []
    except:
        return []

# ============================================================================
# COMPARATEUR MULTI-ACTIFS
# ============================================================================

def build_comparison_dataframe(tickers_str: str) -> tuple:
    """Construit matrice de comparaison multi-actifs."""
    symbols = [s.strip().upper() for s in tickers_str.split(",") if s.strip()]
    
    if not symbols:
        return None, "Entrez au moins un ticker"
    
    rows = []
    
    for symbol in symbols:
        data = fetch_ticker_data(symbol)
        
        if data["error"]:
            rows.append({
                "Ticker": symbol,
                "Prix €": "N/A",
                "Capitalisation": "N/A",
                "Score": "N/A",
                "PER": "N/A",
                "Marge Nette": "N/A",
                "Det/EBITDA": "N/A",
            })
            continue
        
        val = calculate_valuation_metrics(data)
        prof = calculate_profitability_metrics(data)
        health = calculate_financial_health(data)
        score_data = calculate_fundamental_score(data, val, prof, health, 
                                                  calculate_growth_metrics(data))
        
        current_price = safe_float(data["info"].get("currentPrice"))
        current_price_eur = (current_price * data["eur_rate"]) if current_price else None
        market_cap = safe_float(data["info"].get("marketCap"))
        market_cap_formatted = format_large_number(market_cap) if market_cap else "N/A"
        
        rows.append({
            "Ticker": symbol,
            "Prix €": f"{current_price_eur:.2f}" if current_price_eur else "N/A",
            "Capitalisation": market_cap_formatted,
            "Score": f"{score_data['score']}/100",
            "PER": f"{val['per_trailing']:.1f}" if val['per_trailing'] else "N/A",
            "Marge Nette": safe_pct(prof['profit_margin']),
            "Det/EBITDA": f"{health['net_debt_ebitda']:.1f}" if isinstance(health['net_debt_ebitda'], (int, float)) else health['net_debt_ebitda'] or "N/A",
        })
    
    df = pd.DataFrame(rows)
    return df.sort_values("Score", ascending=False, key=lambda x: x.str.extract('(\d+)', expand=False).astype(float)), None

# ============================================================================
# GRAPHIQUES PLOTLY
# ============================================================================

def create_price_chart_with_indicators(hist_data: pd.DataFrame, symbol: str) -> go.Figure:
    """Graphique prix + SMA 50/200 + RSI."""
    if hist_data is None or len(hist_data) < 50:
        return None
    
    hist = hist_data.sort_index()
    
    # SMA
    sma50 = hist["Close"].rolling(50).mean()
    sma200 = hist["Close"].rolling(200).mean()
    
    # RSI (14 jours)
    delta = hist["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Graphique principal
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        mode='lines', name=f'{symbol} Prix',
        line=dict(color='#1f77b4', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=sma50.index, y=sma50,
        mode='lines', name='SMA 50',
        line=dict(color='#ff7f0e', dash='dash', width=1)
    ))
    
    fig.add_trace(go.Scatter(
        x=sma200.index, y=sma200,
        mode='lines', name='SMA 200',
        line=dict(color='#d62728', dash='dash', width=1)
    ))
    
    # Sous-graphique RSI
    fig.add_trace(go.Scatter(
        x=rsi.index, y=rsi,
        mode='lines', name='RSI (14)',
        line=dict(color='#2ca02c', width=1.5),
        yaxis='y2'
    ))
    
    # Lignes seuil RSI
    fig.add_hline(y=70, line_dash="dot", line_color="red", secondary_y=True, annotation_text="Suracheté (70)")
    fig.add_hline(y=30, line_dash="dot", line_color="green", secondary_y=True, annotation_text="Survendu (30)")
    
    fig.update_layout(
        title=f"Analyse Technique {symbol} (5 ans)",
        xaxis_title="Date",
        yaxis_title="Prix",
        yaxis2=dict(title="RSI", range=[0, 100], overlaying='y', side='right'),
        hovermode='x unified',
        template='plotly_dark',
        height=500,
        margin=dict(r=80)
    )
    
    return fig

def create_dca_chart(dca_result: dict) -> go.Figure:
    """Graphique DCA : Capital Investi vs Valeur Portefeuille."""
    if dca_result.get("error"):
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dca_result["timeline"],
        y=dca_result["invested"],
        fill='tozeroy',
        mode='lines',
        name='Capital Investi',
        line=dict(color='#ff7f0e', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=dca_result["timeline"],
        y=dca_result["portfolio"],
        fill='tozeroy',
        mode='lines',
        name='Valeur Portefeuille',
        line=dict(color='#2ca02c', width=2)
    ))
    
    fig.update_layout(
        title="Simulation DCA - Capital Investi vs Valeur Réelle",
        xaxis_title="Date",
        yaxis_title="Montant (€)",
        hovermode='x unified',
        template='plotly_dark',
        height=500
    )
    
    return fig

# ============================================================================
# INTERFACE PRINCIPALE - STREAMLIT
# ============================================================================

def main():
    # Header
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown("### 📈")
    with col2:
        st.markdown("# <span style='color:#1f77b4'>Alpha Terminal Pro</span>", unsafe_allow_html=True)
    
    st.markdown("**Terminal Financier Professionnel | Analyse Actions & ETF | Données Temps Réel**", 
                help="Dernière version - 2026")
    st.divider()
    
    # Sidebar Navigation
    page = st.sidebar.radio(
        "**Navigation**",
        ["🔍 Analyse Action/ETF", "📊 Comparateur", "💰 Simulateur DCA", "ℹ️ À Propos"]
    )
    
    # ========== PAGE 1: ANALYSE ACTION/ETF ==========
    if page == "🔍 Analyse Action/ETF":
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            ticker_input = st.text_input(
                "Entrez le ticker (ex: AAPL, LVMH.PA, CW8.PA)",
                placeholder="Exemple: MSFT, ASML.AS, ESE.PA"
            ).strip().upper()
        
        with col_btn:
            analyze_btn = st.button("🔎 Analyser", use_container_width=True)
        
        if analyze_btn and ticker_input:
            with st.spinner(f"⏳ Récupération données pour {ticker_input}..."):
                data = fetch_ticker_data(ticker_input)
            
            if data["error"]:
                st.error(f"❌ Erreur: {data['error']}")
                st.info("Vérifiez le ticker et votre connexion")
            else:
                # === BLOC SUPÉRIEUR: Infos Clés ===
                info = data["info"]
                current_price = safe_float(info.get("currentPrice"))
                current_price_eur = (current_price * data["eur_rate"]) if current_price else None
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Cours Actuel €",
                        f"{current_price_eur:.2f}" if current_price_eur else "N/A",
                        delta=safe_str(info.get("currency"))
                    )
                
                with col2:
                    st.metric(
                        "Capitalisation",
                        format_large_number(info.get("marketCap"))
                    )
                
                with col3:
                    st.metric(
                        "Volume (24h)",
                        format_large_number(info.get("volume"))
                    )
                
                with col4:
                    score_data = calculate_fundamental_score(
                        data,
                        calculate_valuation_metrics(data),
                        calculate_profitability_metrics(data),
                        calculate_financial_health(data),
                        calculate_growth_metrics(data)
                    )
                    st.metric(
                        "Score Fondamental",
                        f"{score_data['score']}/100",
                        delta=score_data['level']
                    )
                
                st.divider()
                
                # === ONGLETS D'ANALYSE ===
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📊 Ratios Fondamentaux",
                    "📈 Technique & Tendance",
                    "💼 Consensus Analystes",
                    "🎯 Simulateur DCA",
                    "📰 Actualités"
                ])
                
                # TAB 1: Ratios
                with tab1:
                    if data["is_etf"]:
                        st.markdown("### 🎯 Profil ETF")
                        etf_data = analyze_etf(data)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Frais de Gestion (TER)", safe_pct(etf_data["ter"], 3) if etf_data["ter"] else "N/A")
                        with col2:
                            st.metric("Encours (AUM)", f"{etf_data['aum_millions']:.0f}M€" if etf_data["aum_millions"] else "N/A")
                        with col3:
                            st.metric("Distribution", etf_data["distribution"])
                        
                        if etf_data["low_aum_alert"]:
                            st.warning("⚠️ Encours < 100M€ : Risque de liquidité réduite")
                        
                        st.info(f"**Éligibilité PEA:** {etf_data['pea_eligible']}")
                    
                    else:
                        st.markdown("### 📊 Ratios de Valorisation")
                        val = calculate_valuation_metrics(data)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("PER (Trailing)", f"{val['per_trailing']:.1f}" if val['per_trailing'] else "N/A")
                        with col2:
                            st.metric("PER (Forward)", f"{val['per_forward']:.1f}" if val['per_forward'] else "N/A")
                        with col3:
                            st.metric("P/S Ratio", f"{val['ps_ratio']:.2f}" if val['ps_ratio'] else "N/A")
                        with col4:
                            st.metric("P/B Ratio", f"{val['pb_ratio']:.2f}" if val['pb_ratio'] else "N/A")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("EV/EBITDA", f"{val['ev_ebitda']:.1f}" if val['ev_ebitda'] else "N/A")
                        with col2:
                            st.metric("BPA (EPS) €", f"{val['eps_eur']:.2f}" if val['eps_eur'] else "N/A")
                        with col3:
                            st.metric("Valeur Comptable €", f"{val['book_value_eur']:.2f}" if val['book_value_eur'] else "N/A")
                        with col4:
                            st.metric("Prix Graham", f"{val['graham_price']:.2f}" if val['graham_price'] else "N/A")
                        
                        st.markdown("### 📈 Ratios de Rentabilité")
                        prof = calculate_profitability_metrics(data)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Marge Brute", safe_pct(prof['gross_margin']))
                        with col2:
                            st.metric("Marge Opérationnelle", safe_pct(prof['operating_margin']))
                        with col3:
                            st.metric("Marge Nette", safe_pct(prof['profit_margin']))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("ROE", safe_pct(prof['roe']))
                        with col2:
                            st.metric("ROA", safe_pct(prof['roa']))
                        
                        st.markdown("### 💰 Santé Financière")
                        health = calculate_financial_health(data)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Dette Nette", f"{health['net_debt_millions']:.0f}M€" if health['net_debt_millions'] else "N/A")
                        with col2:
                            st.metric("EBITDA", f"{health['ebitda_millions']:.0f}M€" if health['ebitda_millions'] else "N/A")
                        with col3:
                            st.metric("Det Nette/EBITDA", 
                                    f"{health['net_debt_ebitda']:.1f}x" if isinstance(health['net_debt_ebitda'], (int, float)) 
                                    else health['net_debt_ebitda'] or "N/A")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Current Ratio", f"{health['current_ratio']:.2f}" if health['current_ratio'] else "N/A")
                        with col2:
                            st.metric("Quick Ratio", f"{health['quick_ratio']:.2f}" if health['quick_ratio'] else "N/A")
                        with col3:
                            st.metric("Debt/Equity", f"{health['debt_to_equity_pct']:.0f}%" if health['debt_to_equity_pct'] else "N/A")
                        
                        st.markdown("### 📊 Croissance & Dividendes")
                        growth = calculate_growth_metrics(data)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Croissance CA", safe_pct(growth['revenue_growth']))
                        with col2:
                            st.metric("Taux Distribution", safe_pct(growth['payout_ratio']))
                
                # TAB 2: Technique
                with tab2:
                    st.markdown("### 📈 Analyse Technique (5 ans)")
                    
                    fig = create_price_chart_with_indicators(data["hist"], ticker_input)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Données insuffisantes pour le graphique technique")
                
                # TAB 3: Consensus
                with tab3:
                    st.markdown("### 📋 Consensus Analystes")
                    
                    target_price = safe_float(info.get("targetPrice"))
                    current = safe_float(info.get("currentPrice"))
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Objectif Cours €", 
                                f"{target_price * data['eur_rate']:.2f}" if target_price else "N/A")
                    with col2:
                        potential = ((target_price - current) / current * 100) if target_price and current else None
                        st.metric("Potentiel", f"{potential:.1f}%" if potential else "N/A")
                    with col3:
                        st.metric("Recommandation", safe_str(info.get("recommendationKey", "N/A")))
                    
                    num_analysts = info.get("numberOfAnalysts", "N/A")
                    st.info(f"**Nombre d'analystes:** {num_analysts}")
                
                # TAB 4: DCA
                with tab4:
                    st.markdown("### 💰 Simulateur Dollar Cost Averaging")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        monthly = st.slider("Montant mensuel (€)", 50, 1000, 150, step=50)
                    with col2:
                        years = st.selectbox("Période (ans)", [1, 3, 5, 10])
                    
                    if st.button("🚀 Lancer Simulation DCA"):
                        with st.spinner("Calcul en cours..."):
                            dca_result = simulate_dca(data, monthly, years)
                        
                        if dca_result.get("error"):
                            st.error(f"❌ {dca_result['error']}")
                        else:
                            # Graphique
                            fig = create_dca_chart(dca_result)
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Résultats
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Capital Investi", f"€{dca_result['total_invested']:.0f}")
                            with col2:
                                st.metric("Valeur Finale", f"€{dca_result['final_value']:.0f}")
                            with col3:
                                st.metric("Plus-Value", f"€{dca_result['gain']:.0f}")
                            with col4:
                                st.metric("Rendement", f"{dca_result['gain_pct']:.1f}%")
                            
                            st.success(f"✅ **{dca_result['shares']:.4f}** actions accumulées")
                
                # TAB 5: News
                with tab5:
                    st.markdown("### 📰 Actualités Récentes")
                    
                    news = get_ticker_news(data)
                    
                    if not news:
                        st.info("Aucune actualité disponible actuellement")
                    else:
                        for article in news:
                            title = article.get("title", "Sans titre")
                            link = article.get("link", "#")
                            source = article.get("publisher", "Source inconnue")
                            
                            st.markdown(f"""
                            **[{title}]({link})**
                            
                            _Source: {source}_
                            """)
                            st.divider()
    
    # ========== PAGE 2: COMPARATEUR ==========
    elif page == "📊 Comparateur":
        st.markdown("### 📊 Comparateur Multi-Actifs")
        st.markdown("Entrez plusieurs tickers séparés par des virgules pour les comparer")
        
        tickers_input = st.text_input(
            "Tickers",
            placeholder="Ex: AAPL, MSFT, LVMH.PA, ASML.AS"
        )
        
        if st.button("🔄 Générer Comparaison"):
            if tickers_input:
                with st.spinner("Analyse en cours..."):
                    df, error = build_comparison_dataframe(tickers_input)
                
                if error:
                    st.error(f"❌ {error}")
                elif df is not None:
                    st.dataframe(df, use_container_width=True)
                    
                    # Export CSV
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv,
                        file_name=f"comparaison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("Entrez au moins un ticker")
    
    # ========== PAGE 3: SIMULATEUR DCA INDÉPENDANT ==========
    elif page == "💰 Simulateur DCA":
        st.markdown("### 💰 Simulateur DCA Premium")
        
        ticker = st.text_input("Ticker", placeholder="Ex: AAPL").strip().upper()
        monthly = st.slider("Montant mensuel (€)", 50, 2000, 200, step=50)
        years = st.selectbox("Période (ans)", [1, 3, 5, 10])
        
        if st.button("🚀 Lancer Simulation"):
            if not ticker:
                st.warning("Entrez un ticker")
            else:
                with st.spinner("Récupération données..."):
                    data = fetch_ticker_data(ticker)
                
                if data["error"]:
                    st.error(f"❌ {data['error']}")
                else:
                    with st.spinner("Calcul simulation..."):
                        dca = simulate_dca(data, monthly, years)
                    
                    if dca.get("error"):
                        st.error(f"❌ {dca['error']}")
                    else:
                        fig = create_dca_chart(dca)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("### 📊 Résultats Finaux")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Capital Investi Total", f"€{dca['total_invested']:.2f}")
                            st.metric("Plus-Value Brute", f"€{dca['gain']:.2f}")
                        with col2:
                            st.metric("Valeur Finale", f"€{dca['final_value']:.2f}")
                            st.metric("Rendement %", f"{dca['gain_pct']:.2f}%")
                        
                        st.success(f"✅ Actions cumulées: **{dca['shares']:.6f}** | Achat moyen: **€{dca['total_invested']/dca['shares']:.2f}**")
    
    # ========== PAGE 4: À PROPOS ==========
    else:
        st.markdown("### ℹ️ À Propos d'Alpha Terminal Pro")
        
        st.markdown("""
        **Alpha Terminal Pro** est un terminal financier professionnel construit avec Streamlit, yfinance et Plotly.
        
        #### 🎯 Fonctionnalités Principales
        - ✅ Analyse de **21 ratios financiers** complets
        - ✅ Détection automatique d'ETF avec analyse spécifique
        - ✅ Scoring fondamental 0-100 basé sur règles strictes
        - ✅ Convertisseur de devises automatique (USD, GBP, CHF, CAD, JPY...)
        - ✅ Graphiques technique pro (SMA 50/200, RSI 14)
        - ✅ Simulateur DCA haute précision
        - ✅ Comparateur multi-actifs avec export CSV
        - ✅ Flux d'actualités en temps réel
        
        #### 🔒 Sécurité & Fiabilité
        - Parsing défensif avec gestion d'erreurs complète
        - Fallback automatique pour données manquantes
        - Taux de change en cache avec fallback
        - Aucun crash applicatif même si API échoue
        
        #### 📊 Sources de Données
        - **Données temps réel:** Yahoo Finance (yfinance)
        - **Devises:** Taux EUR via Yahoo Finance
        - **Actualités:** Flux RSS intégré yfinance
        
        ---
        
        **Version:** 2.0 Pro | **Dernière mise à jour:** Mai 2026
        
        **Développé par:** Équipe Quantitative Finance 📈
        """)

if __name__ == "__main__":
    main()
