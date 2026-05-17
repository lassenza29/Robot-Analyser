import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
from datetime import datetime
import numpy as np

# Configuration de la page de niveau institutionnel
st.set_page_config(page_title="Terminal Alpha Pro", page_icon="🏛️", layout="wide")

# Style CSS personnalisé pour masquer les imperfections et faire "Sleek/Pro"
st.markdown("""
    <style>
        .reportview-container { background: #0e1117; }
        .metric-card { background-color: #161b22; border-radius: 8px; padding: 15px; border: 1px solid #30363d; }
        div.stButton > button:first-child { background-color: #238636; color: white; border: none; width: 100%; }
        div.stButton > button:first-child:hover { background-color: #2ea043; }
    </style>
""", unsafe_allow_html=True)

# --- CACHE DES TAUX DE CHANGE ---
@st.cache_data(ttl=3600)
def get_conversion_rate(from_currency):
    """Récupère de manière ultra-robuste le taux de change vers l'Euro"""
    from_currency = str(from_currency).upper().strip()
    if not from_currency or from_currency == "EUR" or from_currency == "NONE":
        return 1.0
    try:
        ticker_name = f"{from_currency}EUR=X"
        data = yf.Ticker(ticker_name).history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
        # Fallback pour les monnaies courantes au cas où l'API de change saute
        fallbacks = {"USD": 0.92, "GBp": 0.012, "GBP": 1.17, "CHF": 1.03, "CAD": 0.68, "JPY": 0.006}
        return fallbacks.get(from_currency, 1.0)
    except:
        return 1.0

# --- UTILITAIRES DE PARSING DÉFENSIFS ---
def safe_float(d, key, multiplier=1.0, fallback=0.0):
    val = d.get(key)
    if val is None:
        return fallback
    try:
        return float(val) * multiplier
    except (ValueError, TypeError):
        return fallback

def safe_pct(d, key, fallback=0.0):
    """Gère les cas où yfinance renvoie 0.15 pour 15% ou directement 15"""
    val = d.get(key)
    if val is None:
        return fallback
    try:
        f_val = float(val)
        # Si la valeur absolue est inférieure à 1.0 (ex: 0.12), on multiplie par 100 pour avoir des % clairs
        if abs(f_val) <= 1.0 and f_val != 0.0:
            return f_val * 100.0
        return f_val
    except (ValueError, TypeError):
        return fallback

def safe_str(d, key, fallback="N/A"):
    val = d.get(key)
    return str(val).strip() if val is not None else fallback

def calculer_rsi_pro(prices, window=14):
    if len(prices) < window:
        return pd.Series(index=prices.index, data=50.0)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

# --- PARSER DE DONNÉES DE HAUTE QUALITÉ ---
def analyser_valeur_complete(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or ('shortName' not in info and 'longName' not in info):
            return None
        
        # Gestion de la devise et du taux de change
        currency = safe_str(info, 'currency', 'EUR')
        # Cas spécifique des centimes de livre sterling courants sur yfinance
        fx_mult = 0.01 if currency == "GBp" else 1.0
        rate = get_conversion_rate(currency) * fx_mult
        
        nom = info.get('longName') or info.get('shortName') or ticker_symbol
        is_etf = safe_str(info, 'quoteType').upper() == "ETF"
        
        prix_eur = (safe_float(info, 'currentPrice') or safe_float(info, 'regularMarketPrice') or safe_float(info, 'previousClose')) * rate
        if prix_eur == 0:
            return None
            
        if is_etf:
            frais = safe_pct(info, 'expenseRatio')
            encours = safe_float(info, 'totalAssets', 1 / 1_000_000) * rate
            if encours == 0:
                encours = safe_float(info, 'marketCap', 1 / 1_000_000) * rate
            yield_etf = safe_pct(info, 'trailingAnnualDividendYield') or safe_pct(info, 'yield')
            
            # Score ETF
            score = 0
            if 0 < frais <= 0.2: score += 40
            elif 0 < frais <= 0.5: score += 20
            if encours > 500: score += 40
            elif encours > 100: score += 20
            if yield_etf > 0: score += 20
            
            return {
                "is_etf": True, "nom": nom, "prix": prix_eur, "frais": frais,
                "encours": encours, "rendement": yield_etf, "score": score, "ticker_obj": ticker, "rate": rate
            }
        
        # --- MODULE ACTION : EXTRACTION STRICTE DES 21 RATIOS ET CRITÈRES ---
        # 1. Valorisation
        per = safe_float(info, 'trailingPE', fallback=None)
        forward_per = safe_float(info, 'forwardPE', fallback=None)
        ps_ratio = safe_float(info, 'priceToSalesTrailing12Months')
        pb_ratio = safe_float(info, 'priceToBook')
        ev_ebitda = safe_float(info, 'enterpriseToEbitda')
        bna = safe_float(info, 'trailingEps') * rate
        v_book = safe_float(info, 'bookValue') * rate
        prod_graham = 22.5 * bna * v_book
        prix_graham = math.sqrt(prod_graham) if prod_graham > 0 else 0.0
        
        # 2. Rentabilité
        marge_brute = safe_pct(info, 'grossMargins')
        marge_expl = safe_pct(info, 'operatingMargins')
        marge_nette = safe_pct(info, 'profitMargins')
        roe = safe_pct(info, 'returnOnEquity')
        roa = safe_pct(info, 'returnOnAssets')
        
        # 3. Santé financière & Bilan
        cap_boursiere = safe_float(info, 'marketCap', 1 / 1_000_000) * rate
        dette_totale = safe_float(info, 'totalDebt', 1 / 1_000_000) * rate
        tresorerie = safe_float(info, 'totalCash', 1 / 1_000_000) * rate
        dette_nette = dette_totale - tresorerie
        ebitda = safe_float(info, 'ebitda', 1 / 1_000_000) * rate
        ratio_dette_ebitda = dette_nette / ebitda if ebitda > 0 else (0.0 if dette_nette <= 0 else float('inf'))
        current_ratio = safe_float(info, 'currentRatio')
        quick_ratio = safe_float(info, 'quickRatio')
        debt_equity = safe_float(info, 'debtToEquity')
        
        # 4. Croissance & Dividendes
        croissance_ca_5a = safe_pct(info, 'revenueGrowth') # proxy direct trimestriel ou historique disponible
        payout_ratio = safe_pct(info, 'payoutRatio')
        div_yield = safe_pct(info, 'dividendYield')
        
        # 5. Consensus & Avis du Marché
        target_price = safe_float(info, 'targetMeanPrice') * rate
        reco = safe_str(info, 'recommendationKey', 'inconnu').lower()
        nb_analystes = safe_float(info, 'numberOfAnalystOpinions')
        
        # --- CALCUL DU SCORE DE QUALITÉ GLOBAL DE L'ACTION (SUR 100) ---
        score = 0
        if ratio_dette_ebitda < 2.0: score += 15
        elif ratio_dette_ebitda < 3.5: score += 5
        if roe > 15.0: score += 15
        if marge_nette > 12.0: score += 15
        if current_ratio > 1.2: score += 10
        if 0.1 < payout_ratio < 75.0: score += 15
        if prix_graham > prix_eur: score += 15
        if reco in ['buy', 'strong_buy']: score += 15
        
        return {
            "is_etf": False, "nom": nom, "prix": prix_eur, "cap": cap_boursiere, "score": score,
            "ticker_obj": ticker, "rate": rate, "reco": reco, "target": target_price, "nb_analystes": nb_analystes,
            # Les 21 Ratios / Critères bien packagés pour l'affichage
            "ratios": {
                "PER Actuel": (per, "x"),
                "PER Futur (Forward)": (forward_per, "x"),
                "Price to Sales (P/S)": (ps_ratio, "x"),
                "Price to Book (P/B)": (pb_ratio, "x"),
                "Valeur d'Entreprise / EBITDA": (ev_ebitda, "x"),
                "Bénéfice par Action (BPA)": (bna, "€"),
                "Valeur Comptable par Action": (v_book, "€"),
                "Prix Théorique de Graham": (prix_graham, "€"),
                "Marge Brute": (marge_brute, "%"),
                "Marge Opérationnelle": (marge_expl, "%"),
                "Marge Nette": (marge_nette, "%"),
                "Rendement des Capitaux Propres (ROE)": (roe, "%"),
                "Rendement des Actifs (ROA)": (roa, "%"),
                "Dette Nette": (dette_nette, "M€"),
                "EBITDA": (ebitda, "M€"),
                "Ratio Dette Nette / EBITDA": (ratio_dette_ebitda, "x"),
                "Liquidité Générale (Current Ratio)": (current_ratio, "x"),
                "Liquidité Immédiate (Quick Ratio)": (quick_ratio, "x"),
                "Ratio Dette / Capitaux Propres": (debt_equity, "%"),
                "Croissance Trimestrielle du CA": (croissance_ca_5a, "%"),
                "Taux de Distribution (Payout Ratio)": (payout_ratio, "%"),
                "Rendement du Dividende (Yield)": (div_yield, "%")
            }
        }
    except:
        return None

# =========================================================
# ARCHITECTURE INTERFACE STREAMLIT
# =========================================================
st.title("🏛️ Terminal Financier Pro & Gestion d'Actifs")
st.markdown("Analyses fondamentales avancées, monitoring des critères de risque et simulateurs haute précision.")

menu_principal = st.sidebar.radio("Sélectionnez le module de travail 🛠️", ["Recherche & Ratios Avancés", "Comparateur de Portefeuille"])

if menu_principal == "Recherche & Ratios Avancés":
    ticker_s = st.text_input("🔍 Saisissez un symbole boursier (ex: AAPL, LVMH.PA, MSFT, CW8.PA) :", value="AAPL").upper().strip()
    
    if ticker_s:
        with st.spinner("Extraction des rapports financiers et synchronisation des devises..."):
            d = analyser_valeur_complete(ticker_s)
            
            if not d:
                st.error("❌ Impossible de récupérer ou de traiter les données pour ce symbole. Vérifiez l'extension (.PA pour Paris, etc.).")
            else:
                if d["is_etf"]:
                    # ==========================================
                    # INTERFACE PRO POUR LES ETF
                    # ==========================================
                    st.header(f"📊 Fiche ETF : {d['nom']} ({ticker_s})")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Prix d'Achat (€)", f"{d['prix']:,.2f} €")
                    c2.metric("Frais sur Encours (TER)", f"{d['frais']:.2f} %" if d['frais'] > 0 else "N/A")
                    c3.metric("Actifs Sous Gestion", f"{d['encours']:,.1f} M€" if d['encours'] > 0 else "N/A")
                    c4.metric("Rendement Annuel", f"{d['rendement']:.2f} %" if d['rendement'] > 0 else "0.00 % / Capitalisation")
                    
                    st.markdown(f"**Score d'Évaluation de l'ETF :** {d['score']} / 100")
                    st.progress(d['score'] / 100)
                    
                else:
                    # ==========================================
                    # INTERFACE PRO POUR LES ACTIONS
                    # ==========================================
                    st.header(f"🏢 Analyse Fondamentale : {d['nom']} ({ticker_s})")
                    
                    # Bloc Score, Prix et Consensus Récapitulatif
                    col_top1, col_top2, col_top3 = st.columns([1, 1, 2])
                    with col_top1:
                        st.metric("Dernier Cours Réel", f"{d['prix']:,.2f} €")
                    with col_top2:
                        st.metric("Capitalisation", f"{d['cap']:,.0f} M€")
                    with col_top3:
                        reco_fr = {"buy": "Achat", "strong_buy": "Achat Fort", "hold": "Conserver", "sell": "Vendre", "strong_sell": "Vente Forte"}.get(d['reco'], "Neutre / Inconnu")
                        st.markdown(f"**Avis global des marchés :** `{reco_fr.upper()}`")
                        if d['target'] > 0:
                            st.markdown(f"Objectif moyen des analystes : **{d['target']:,.2f} €** (sur {int(d['nb_analystes'])} avis)")
                    
                    st.markdown(f"**Score de Qualité Fondamentale :** {d['score']} / 100")
                    st.progress(d['score'] / 100)
                    
                    # LES STRUCTURES D'ONGLETS SÉCURISÉES
                    t1, t2, t3, t4 = st.tabs(["📋 Les 21 Ratios & Critères", "📈 Graphique Pro & Timing RSI", "⏱️ Simulateur DCA Institutionnel", "📰 Flux d'Actualités"])
                    
                    with t1:
                        st.subheader("Tableau de Bord Complet des Ratios Réglementaires")
                        # Affichage propre sous forme de grille 3x7 ou sous-sections thématiques claires
                        rat = d["ratios"]
                        
                        sec1, sec2, sec3 = st.columns(3)
                        with sec1:
                            st.markdown("#### Valorisation & Prix")
                            for k in ["PER Actuel", "PER Futur (Forward)", "Price to Sales (P/S)", "Price to Book (P/B)", "Valeur d'Entreprise / EBITDA", "Bénéfice par Action (BPA)", "Valeur Comptable par Action", "Prix Théorique de Graham"]:
                                val, unit = rat[k]
                                st.write(f"• **{k} :** {f'{val:,.2f} {unit}' if val is not None and val != float('inf') else 'N/A'}")
                        
                        with sec2:
                            st.markdown("#### Performance & Marges")
                            for k in ["Marge Brute", "Marge Opérationnelle", "Marge Nette", "Rendement des Capitaux Propres (ROE)", "Rendement des Actifs (ROA)"]:
                                val, unit = rat[k]
                                st.write(f"• **{k} :** {f'{val:,.2f} {unit}' if val is not None else 'N/A'}")
                        
                        with sec3:
                            st.markdown("#### Bilan, Risques & Dividendes")
                            for k in ["Dette Nette", "EBITDA", "Ratio Dette Nette / EBITDA", "Liquidité Générale (Current Ratio)", "Liquidité Immédiate (Quick Ratio)", "Ratio Dette / Capitaux Propres", "Croissance Trimestrielle du CA", "Taux de Distribution (Payout Ratio)", "Rendement du Dividende (Yield)"]:
                                val, unit = rat[k]
                                if k == "Ratio Dette Nette / EBITDA" and val == float('inf'):
                                    st.write(f"• **{k} :** N/A (Trésorerie positive)")
                                else:
                                    st.write(f"• **{k} :** {f'{val:,.2f} {unit}' if val is not None else 'N/A'}")
                                    
                    with t2:
                        st.subheader("Analyse de Tendance à Long Terme (Moyennes Mobiles et RSI)")
                        hist = d['ticker_obj'].history(period="5y")
                        if not hist.empty:
                            hist['Close_EUR'] = hist['Close'] * d['rate']
                            hist['SMA50'] = hist['Close_EUR'].rolling(window=50).mean()
                            hist['SMA200'] = hist['Close_EUR'].rolling(window=200).mean()
                            hist['RSI'] = calculer_rsi_pro(hist['Close_EUR'])
                            
                            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close_EUR'], name="Cours (€)", line=dict(color='#58a6ff', width=2)), row=1, col=1)
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], name="MM50 jours", line=dict(color='#ffea7f', width=1)), row=1, col=1)
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], name="MM200 jours", line=dict(color='#ff7b72', width=1.5)), row=1, col=1)
                            
                            fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name="RSI (14)", line=dict(color='#bc8cff', width=1)), row=2, col=1)
                            fig.add_hline(y=70, line_dash="dash", line_color="#ff7b72", row=2, col=1)
                            fig.add_hline(y=30, line_dash="dash", line_color="#56b46c", row=2, col=1)
                            
                            fig.update_layout(height=500, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            last_rsi = hist['RSI'].iloc[-1]
                            st.info(f"💡 **Indicateur de Momentum (RSI) :** Le RSI actuel est à **{last_rsi:.1f}/100**. " + 
                                    ("L'action est techniquement surachetée (zone de surchauffe)." if last_rsi > 70 else "L'action est survendue (opportunité potentielle de point d'entrée)." if last_rsi < 30 else "Le marché est dans une zone d'équilibre neutre."))
                        else:
                            st.warning("Historique de prix indisponible pour générer l'analyse technique.")

                    with t3:
                        st.subheader("Simulateur d'Investissement Programmé Réel (DCA)")
                        st.markdown("Ce simulateur achète des fractions d'actions au prix réel du marché au début de chaque mois à partir de l'historique réel.")
                        
                        c_dca1, c_dca2 = st.columns(2)
                        montant_mensuel = c_dca1.slider("Versement programmé chaque mois (€)", 25, 2000, 150, 25)
                        horizon_annees = c_dca2.slider("Recul historique de la simulation (Années)", 1, 15, 5, 1)
                        
                        hist_dca = d['ticker_obj'].history(period=f"{horizon_annees}y")
                        if not hist_dca.empty:
                            hist_dca['Close_EUR'] = hist_dca['Close'] * d['rate']
                            # Sélectionner le premier cours disponible pour chaque mois
                            points_mensuels = hist_dca['Close_EUR'].resample('MS').first().dropna()
                            
                            dates_sim = []
                            total_investi = 0
                            nb_actions_cumulees = 0
                            valeurs_portefeuille = []
                            capitaux_investis = []
                            
                            for date, prix_mois in points_mensuels.items():
                                total_investi += montant_mensuel
                                nb_actions_cumulees += (montant_mensuel / prix_mois)
                                val_actuelle = nb_actions_cumulees * prix_mois
                                
                                dates_sim.append(date)
                                capitaux_investis.append(total_investi)
                                valeurs_portefeuille.append(val_actuelle)
                            
                            fig_dca = go.Figure()
                            fig_dca.add_trace(go.Scatter(x=dates_sim, y=capitaux_investis, name="Total Investi de votre poche", line=dict(color='gray', dash='dash')))
                            fig_dca.add_trace(go.Scatter(x=dates_sim, y=valeurs_portefeuille, name="Valeur Réelle du Capital", fill='tonexty', line=dict(color='#56b46c')))
                            fig_dca.update_layout(height=400, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
                            st.plotly_chart(fig_dca, use_container_width=True)
                            
                            gain_final = valeurs_portefeuille[-1] - capitaux_investis[-1]
                            perf_pct = (gain_final / capitaux_investis[-1]) * 100
                            st.success(f"📊 **Bilan Final du Plan DCA :** Montant cumulé investi : **{capitaux_investis[-1]:,.0f} €** | Valeur à ce jour : **{valeurs_portefeuille[-1]:,.2f} €** | Plus-value : **{gain_final:+,.2f} €** ({perf_pct:+.2f}%)")
                        else:
                            st.error("Données de prix historiques introuvables pour simuler la stratégie DCA.")

                    with t4:
                        st.subheader("Dernières Dépêches & Flux d'Actualités Financières")
                        try:
                            articles = d['ticker_obj'].news
                            if articles:
                                for art in articles[:5]:
                                    t_title = art.get('title', 'Titre de presse indisponible')
                                    t_link = art.get('link', '#')
                                    t_pub = art.get('publisher', 'Média Financier')
                                    st.markdown(f"🔹 **[{t_title}]({t_link})**")
                                    st.caption(f"Source : {t_pub}")
                                    st.write("---")
                            else:
                                st.info("Aucun flux d'actualité actif sur ce téléscripteur via Yahoo Finance à cette date.")
                        except:
                            st.info("Flux d'actualités temporairement inaccessible.")

# =========================================================
# MODULE COMPARATEUR MULTI-ACTIFS ROBUSTE
# =========================================================
else:
    st.header("🏛️ Comparateur et Classement Multi-Actifs")
    st.markdown("Entrez une liste de tickers financiers pour générer une matrice comparative nettoyée et téléchargeable.")
    
    type_comp = st.radio("Nature des actifs à comparer :", ["Actions mondiales", "ETF (Fonds Indiciels)"])
    
    if type_comp == "Actions mondiales":
        entree = st.text_input("Liste des symboles (séparés par des virgules) :", value="AAPL, MSFT, LVMH.PA, NVDA")
        tickers_liste = [x.strip().upper() for x in entree.split(",") if x.strip()]
        
        if st.button("Lancer la Matrice de Comparaison"):
            lignes = []
            with st.spinner("Construction du tableau comparatif..."):
                for tick in tickers_liste:
                    res = analyser_valeur_complete(tick)
                    if res and not res["is_etf"]:
                        r = res["ratios"]
                        lignes.append({
                            "Ticker": tick,
                            "Nom de l'actif": res["nom"],
                            "Score (/100)": res["score"],
                            "Prix (€)": round(res["prix"], 2),
                            "Cap. (M€)": round(res["cap"], 0),
                            "Dette/EBITDA": round(r["Ratio Dette Nette / EBITDA"][0], 2) if r["Ratio Dette Nette / EBITDA"][0] != float('inf') else "Cash Positif",
                            "Marge Nette (%)": round(r["Marge Nette"][0], 2),
                            "ROE (%)": round(r["Rendement des Capitaux Propres (ROE)"][0], 2),
                            "PER Actuel (x)": round(r["PER Actuel"][0], 2) if r["PER Actuel"][0] is not None else "N/A",
                            "Rendement (%)": round(r["Rendement du Dividende (Yield)"][0], 2)
                        })
            if lignes:
                df_res = pd.DataFrame(lignes)
                # Tri automatique par score décroissant
                df_res = df_res.sort_values(by="Score (/100)", ascending=False)
                st.dataframe(df_res.set_index("Ticker"), use_container_width=True)
                
                # Export sans plantage
                csv_data = df_res.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Télécharger la matrice au format CSV", data=csv_data, file_name="export_comparatif_actions.csv", mime="text/csv")
            else:
                st.error("Aucune donnée valide n'a pu être extraite pour cette liste d'actions.")
                
    else:
        entree = st.text_input("Liste des symboles ETF (séparés par des virgules) :", value="CW8.PA, ESE.PA, SPY")
        tickers_liste = [x.strip().upper() for x in entree.split(",") if x.strip()]
        
        if st.button("Lancer la Matrice de Comparaison ETF"):
            lignes = []
            with st.spinner("Analyse comparative des indices..."):
                for tick in tickers_liste:
                    res = analyser_valeur_complete(tick)
                    if res and res["is_etf"]:
                        lignes.append({
                            "Ticker": tick,
                            "Nom de l'ETF": res["nom"],
                            "Score (/100)": res["score"],
                            "Prix (€)": round(res["prix"], 2),
                            "Frais Annuels (TER %)": round(res["frais"], 2),
                            "Encours (M€)": round(res["encours"], 0),
                            "Rendement du Fonds (%)": round(res["rendement"], 2)
                        })
            if lignes:
                df_res = pd.DataFrame(lignes).sort_values(by="Score (/100)", ascending=False)
                st.dataframe(df_res.set_index("Ticker"), use_container_width=True)
                
                csv_data = df_res.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Télécharger la matrice au format CSV", data=csv_data, file_name="export_comparatif_etf.csv", mime="text/csv")
            else:
                st.error("Aucune donnée valide n'a pu être extraite pour cette liste d'ETF.")
