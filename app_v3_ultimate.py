import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
from datetime import datetime
import numpy as np

# Configuration de la page (Mode Ultime)
st.set_page_config(page_title="Terminal Financier Pro", page_icon="📈", layout="wide")

# --- FONCTIONS DE SÉCURITÉ ET CONVERSION ---
@st.cache_data(ttl=3600)
def get_fx_rate(currency):
    # Récupère le taux de change vers l'Euro pour afficher tout en €
    if not currency or currency.upper() == "EUR":
        return 1.0
    try:
        # Ex: USD -> EUR (EUR=X ou USDEUR=X)
        fx_ticker = f"{currency.upper()}EUR=X"
        fx_data = yf.Ticker(fx_ticker).history(period="1d")
        if not fx_data.empty:
            return fx_data['Close'].iloc[-1]
        return 1.0
    except:
        return 1.0

def get_float(info_dict, key, mult=1.0, default=0.0):
    val = info_dict.get(key)
    if val is None: return default
    try: return float(val) * mult
    except (ValueError, TypeError): return default

def get_str(info_dict, key, default="N/A"):
    val = info_dict.get(key)
    return str(val).strip() if val is not None else default

def calculer_rsi(data, window=14):
    # Calcule le Relative Strength Index (RSI)
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- EXTRACTION DONNÉES ACTION ---
def extraire_donnees_action(ticker_symbole):
    try:
        ticker = yf.Ticker(ticker_symbole)
        info = ticker.info
        if not info or ('shortName' not in info and 'longName' not in info):
            return None
        
        devise = get_str(info, 'currency', 'EUR')
        taux_fx = get_fx_rate(devise)
        
        nom = info.get('longName') or info.get('shortName') or ticker_symbole
        prix_local = get_float(info, 'currentPrice') or get_float(info, 'regularMarketPrice') or get_float(info, 'previousClose')
        prix_eur = prix_local * taux_fx
        cap_eur = get_float(info, 'marketCap', 1 / 1_000_000) * taux_fx
        
        # Bilan
        dette_b = get_float(info, 'totalDebt', 1 / 1_000_000) * taux_fx
        treso = get_float(info, 'totalCash', 1 / 1_000_000) * taux_fx
        if dette_b == 0:
            dette_b = (get_float(info, 'longTermDebt') + get_float(info, 'shortLongTermDebt')) / 1_000_000 * taux_fx
        dette_n = dette_b - treso
        
        ebitda = get_float(info, 'ebitda', 1 / 1_000_000) * taux_fx
        ratio_d_e = dette_n / ebitda if ebitda > 0 else (0.0 if dette_n <= 0 else float('inf'))
        
        ca = get_float(info, 'totalRevenue', 1 / 1_000_000) * taux_fx
        res_expl = (get_float(info, 'operatingIncome', 1 / 1_000_000) or get_float(info, 'operatingCashflow', 1 / 1_000_000)) * taux_fx
        res_net = get_float(info, 'netIncomeToCommon', 1 / 1_000_000) * taux_fx
        marge_expl = get_float(info, 'operatingMargins', 100.0)
        marge_net = get_float(info, 'profitMargins', 100.0)
        
        actions = get_float(info, 'sharesOutstanding')
        actif_net_a_local = get_float(info, 'bookValue')
        actif_net_a_eur = actif_net_a_local * taux_fx
        
        cp = get_float(info, 'totalStockholderEquity', 1 / 1_000_000) * taux_fx
        if cp == 0 and actif_net_a_eur > 0 and actions > 0:
            cp = (actif_net_a_eur * actions) / 1_000_000

        roe = get_float(info, 'returnOnEquity', 100.0)
        bna_local = get_float(info, 'trailingEps') or get_float(info, 'forwardEps')
        bna_eur = bna_local * taux_fx
        per = get_float(info, 'trailingPE')
        
        # Graham
        produit_graham = 22.5 * bna_eur * actif_net_a_eur
        p_graham = math.sqrt(produit_graham) if produit_graham > 0 else 0.0
        
        # Nouveautés : Dividendes & Consensus
        payout_ratio = get_float(info, 'payoutRatio', 100.0)
        div_yield = get_float(info, 'dividendYield', 100.0)
        target_price_eur = get_float(info, 'targetMeanPrice') * taux_fx
        reco = get_str(info, 'recommendationKey', 'inconnu')
        nb_analystes = get_float(info, 'numberOfAnalystOpinions')
        
        # --- SCORING GLOBAL ACTION (Sur 100) ---
        score = 0
        if ratio_d_e < 2: score += 20
        elif ratio_d_e < 3: score += 10
        if roe > 15: score += 20
        elif roe > 10: score += 10
        if marge_net > 10: score += 15
        elif marge_net > 5: score += 5
        if p_graham > prix_eur: score += 20
        if 0 < payout_ratio < 70: score += 15
        if ca > 0 and res_net > 0: score += 10
        
        return {
            "nom": nom, "prix": prix_eur, "cap": cap_eur, "dette_b": dette_b, "treso": treso,
            "dette_n": dette_n, "ebitda": ebitda, "ratio_d_e": ratio_d_e, "ca": ca,
            "res_expl": res_expl, "res_net": res_net, "marge_expl": marge_expl,
            "marge_net": marge_net, "cp": cp, "roe": roe, "actions": actions,
            "bna": bna_eur, "per": per, "actif_net_a": actif_net_a_eur, "p_graham": p_graham,
            "payout": payout_ratio, "div_yield": div_yield, "target": target_price_eur, 
            "reco": reco, "nb_analystes": nb_analystes, "score": score,
            "ticker_obj": ticker, "devise_origine": devise, "taux_fx": taux_fx
        }
    except Exception as e:
        return None

# --- EXTRACTION DONNÉES ETF ---
def extraire_donnees_etf(ticker_symbole):
    try:
        ticker = yf.Ticker(ticker_symbole)
        info = ticker.info
        if not info or ('shortName' not in info and 'longName' not in info):
            return None
            
        devise = get_str(info, 'currency', 'EUR')
        taux_fx = get_fx_rate(devise)
        
        nom = info.get('longName') or info.get('shortName') or ticker_symbole
        prix = (get_float(info, 'regularMarketPrice') or get_float(info, 'previousClose')) * taux_fx
        frais = get_float(info, 'expenseRatio', 100.0)
        encours = (get_float(info, 'totalAssets', 1 / 1_000_000) or get_float(info, 'marketCap', 1 / 1_000_000)) * taux_fx
        rendement = get_float(info, 'trailingAnnualDividendYield', 100.0) or get_float(info, 'yield', 100.0)
        
        # --- SCORING GLOBAL ETF (Sur 100) ---
        score = 0
        if 0 < frais <= 0.2: score += 30
        elif 0 < frais <= 0.4: score += 15
        if encours > 500: score += 30
        elif encours > 100: score += 15
        if rendement > 2.0: score += 20
        # Les 20 derniers points pour la présence de données claires
        if encours > 0 and frais > 0: score += 20
        
        return {
            "nom": nom, "prix": prix, "frais": frais, "encours": encours, "rendement": rendement, 
            "score": score, "ticker_obj": ticker, "taux_fx": taux_fx
        }
    except Exception:
        return None

# =========================================================
# INTERFACE UTILISATEUR PRINCIPALE
# =========================================================
st.title("🏛️ Terminal Financier Pro")
st.markdown("Analyses fondamentales, scoring, techniques, dividendes, DCA et Consensus (**Données converties en Euros €**).")

onglets_sidebar = st.sidebar.radio("Navigation 🛠️", ["Recherche Détaillée", "Comparateur Multi-Actifs"])

if onglets_sidebar == "Recherche Détaillée":
    ticker_symbole = st.text_input("🔍 Entrez le symbole (ex: AAPL, RMS.PA, CW8.PA) :", value="AAPL").upper().strip()
    
    if ticker_symbole:
        with st.spinner("Analyse approfondie en cours..."):
            try:
                ticker = yf.Ticker(ticker_symbole)
                info = ticker.info
                
                if not info or ('shortName' not in info and 'longName' not in info):
                    st.error("❌ Symbole introuvable.")
                else:
                    quote_type = get_str(info, 'quoteType').upper()
                    
                    if quote_type == "ETF":
                        # ================== MODULE ETF ==================
                        d = extraire_donnees_etf(ticker_symbole)
                        if d:
                            st.header(f"📊 ETF : {d['nom']} ({ticker_symbole})")
                            
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Prix Actuel", f"{d['prix']:,.2f} €")
                            c2.metric("Frais (TER)", f"{d['frais']:.2f} %" if d['frais'] > 0 else "N/A")
                            c3.metric("Encours", f"{d['encours']:,.0f} M€" if d['encours'] > 0 else "N/A")
                            c4.metric("Rendement", f"{d['rendement']:.2f} %" if d['rendement'] > 0 else "N/A / Acc")
                            
                            st.progress(d['score'] / 100)
                            st.caption(f"**Score de Qualité ETF : {d['score']}/100** (Basé sur les frais et la liquidité)")
                            
                            # BACKTESTER DCA (ETF)
                            st.divider()
                            st.subheader("⏱️ Simulateur DCA (Investissement Programmé)")
                            col_dca1, col_dca2 = st.columns(2)
                            mensualite = col_dca1.slider("Investissement mensuel (€)", 50, 1000, 150, 50)
                            annees = col_dca2.slider("Durée du backtest (Années)", 1, 15, 5, 1)
                            
                            hist = d['ticker_obj'].history(period=f"{annees}y")
                            if not hist.empty:
                                hist['Close_EUR'] = hist['Close'] * d['taux_fx']
                                monthly = hist['Close_EUR'].resample('ME').last().dropna()
                                invested_capital = []
                                portfolio_value = []
                                total_shares = 0
                                total_invested = 0
                                
                                for price in monthly:
                                    shares_bought = mensualite / price
                                    total_shares += shares_bought
                                    total_invested += mensualite
                                    
                                    invested_capital.append(total_invested)
                                    portfolio_value.append(total_shares * price)
                                
                                fig_dca = go.Figure()
                                fig_dca.add_trace(go.Scatter(x=monthly.index, y=invested_capital, mode='lines', name='Capital Investi (€)', line=dict(color='gray', dash='dash')))
                                fig_dca.add_trace(go.Scatter(x=monthly.index, y=portfolio_value, mode='lines', name='Valeur du Portefeuille (€)', fill='tonexty', line=dict(color='green')))
                                fig_dca.update_layout(title=f"Simulation DCA : {mensualite}€/mois pendant {annees} ans", yaxis_title="Euros (€)", template="plotly_dark")
                                st.plotly_chart(fig_dca, use_container_width=True)
                                
                                final_val = portfolio_value[-1]
                                st.success(f"Bilan : Total investi = **{total_invested:,.0f} €** | Valeur finale = **{final_val:,.0f} €** (Perf: **{((final_val/total_invested)-1)*100:.2f}%**)")
                            else:
                                st.info("Historique insuffisant pour le simulateur.")

                    else:
                        # ================== MODULE ACTION ==================
                        d = extraire_donnees_action(ticker_symbole)
                        if d:
                            st.header(f"🏢 {d['nom']} ({ticker_symbole})")
                            
                            # SCORE GLOBAL ET RESUME
                            col_score1, col_score2 = st.columns([1, 3])
                            with col_score1:
                                color = "green" if d['score'] >= 70 else ("orange" if d['score'] >= 40 else "red")
                                st.markdown(f"<h1 style='text-align: center; color: {color}; font-size: 3rem;'>{d['score']}/100</h1>", unsafe_allow_html=True)
                                st.markdown("<p style='text-align: center;'>Score de Qualité</p>", unsafe_allow_html=True)
                            with col_score2:
                                st.markdown(f"**Prix Actuel :** {d['prix']:,.2f} €")
                                st.markdown(f"**Capitalisation :** {d['cap']:,.0f} M€")
                                if d['reco'] != 'inconnu':
                                    reco_trad = {"buy": "Acheter", "strong_buy": "Achat Fort", "hold": "Conserver", "sell": "Vendre", "strong_sell": "Vente Forte"}.get(d['reco'].lower(), d['reco'])
                                    st.markdown(f"👥 **Avis des Investisseurs & Analystes :** Le consensus est actuellement à **{reco_trad.upper()}** (basé sur {int(d['nb_analystes'])} analystes). Objectif de cours moyen : **{d['target']:,.2f} €**.")
                                else:
                                    st.markdown("👥 **Avis des Investisseurs :** Pas de consensus d'analystes disponible pour cette valeur.")
                            
                            # ONGLET DE NAVIGATION INTERNE
                            tab1, tab2, tab3, tab4 = st.tabs(["📊 Fondamentaux", "📈 Technique & Timing", "💸 Dividendes & DCA", "📰 Actualités"])
                            
                            # --- TAB 1 : FONDAMENTAUX ---
                            with tab1:
                                st.subheader("Santé Financière et Valorisation")
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric("Dette Nette", f"{d['dette_n']:,.0f} M€")
                                c2.metric("Dette / EBITDA", f"{d['ratio_d_e']:.2f} x" if d['ratio_d_e'] != float('inf') else "N/A")
                                c3.metric("Marge Nette", f"{d['marge_net']:.2f} %")
                                c4.metric("ROE", f"{d['roe']:.2f} %")
                                
                                c5, c6, c7, c8 = st.columns(4)
                                c5.metric("PER Actuel", f"{d['per']:.2f} x" if d['per'] else "N/A")
                                c6.metric("Bénéfice par Action", f"{d['bna']:.2f} €")
                                c7.metric("Actif Net / Action", f"{d['actif_net_a']:.2f} €")
                                c8.metric("Prix Graham", f"{d['p_graham']:.2f} €" if d['p_graham'] > 0 else "N/A")

                            # --- TAB 2 : TECHNIQUE & TIMING ---
                            with tab2:
                                st.subheader("Analyse Technique (MM50, MM200 & RSI)")
                                hist = d['ticker_obj'].history(period="3y")
                                if not hist.empty:
                                    hist['Close_EUR'] = hist['Close'] * d['taux_fx']
                                    hist['Open_EUR'] = hist['Open'] * d['taux_fx']
                                    hist['High_EUR'] = hist['High'] * d['taux_fx']
                                    hist['Low_EUR'] = hist['Low'] * d['taux_fx']
                                    
                                    hist['SMA50'] = hist['Close_EUR'].rolling(window=50).mean()
                                    hist['SMA200'] = hist['Close_EUR'].rolling(window=200).mean()
                                    hist['RSI'] = calculer_rsi(hist['Close_EUR'])
                                    
                                    fig_tech = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                                    
                                    # Candlesticks
                                    fig_tech.add_trace(go.Candlestick(x=hist.index, open=hist['Open_EUR'], high=hist['High_EUR'], low=hist['Low_EUR'], close=hist['Close_EUR'], name="Prix"), row=1, col=1)
                                    fig_tech.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='blue', width=1), name='MM 50 Jours'), row=1, col=1)
                                    fig_tech.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='orange', width=2), name='MM 200 Jours'), row=1, col=1)
                                    
                                    # RSI
                                    fig_tech.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], line=dict(color='purple', width=1), name='RSI (14)'), row=2, col=1)
                                    fig_tech.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
                                    fig_tech.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
                                    
                                    fig_tech.update_layout(title="Graphique Technique Interactif", xaxis_rangeslider_visible=False, template="plotly_dark", height=600)
                                    st.plotly_chart(fig_tech, use_container_width=True)
                                    
                                    # Verdict Technique Rapide
                                    dernier_prix = hist['Close_EUR'].iloc[-1]
                                    dernier_rsi = hist['RSI'].iloc[-1]
                                    mm200 = hist['SMA200'].iloc[-1] if not pd.isna(hist['SMA200'].iloc[-1]) else dernier_prix
                                    
                                    etat_tendance = "Haussière 🟢" if dernier_prix > mm200 else "Baissière 🔴"
                                    etat_rsi = "Surachetée ⚠️ (Risque de baisse)" if dernier_rsi > 70 else ("Survendue ✅ (Opportunité)" if dernier_rsi < 30 else "Neutre ⚪")
                                    st.info(f"**Indicateurs Actuels :** Tendance de fond : **{etat_tendance}** | Tension du marché (RSI) : **{etat_rsi}** ({dernier_rsi:.0f}/100)")
                                else:
                                    st.warning("Données historiques insuffisantes pour l'analyse technique.")

                            # --- TAB 3 : DIVIDENDES & DCA ---
                            with tab3:
                                st.subheader("Sécurité des Dividendes")
                                d1, d2 = st.columns(2)
                                d1.metric("Rendement Actuel (Yield)", f"{d['div_yield']:.2f} %")
                                d2.metric("Payout Ratio (Taux de distribution)", f"{d['payout']:.2f} %")
                                
                                if d['payout'] == 0:
                                    st.info("L'entreprise ne verse pas de dividende significatif.")
                                else:
                                    if d['payout'] < 70:
                                        st.success("🟢 Payout Ratio sain (< 70%). Le dividende est couvert par les bénéfices.")
                                    elif d['payout'] > 100:
                                        st.error("🔴 Danger : L'entreprise pioche dans ses réserves ou s'endette pour payer le dividende.")
                                    else:
                                        st.warning("⚠️ Payout Ratio élevé. Marge de sécurité faible.")
                                        
                                    div_history = d['ticker_obj'].dividends
                                    if not div_history.empty:
                                        div_annuel = div_history.resample('YE').sum() * d['taux_fx']
                                        div_annuel = div_annuel.tail(15)
                                        fig_div = go.Figure(go.Bar(x=div_annuel.index.year, y=div_annuel.values, marker_color='gold'))
                                        fig_div.update_layout(title="Historique des Dividendes Versés (en €)", xaxis_title="Année", yaxis_title="Euros (€)", template="plotly_dark")
                                        st.plotly_chart(fig_div, use_container_width=True)
                                        
                                st.divider()
                                st.subheader("⏱️ Simulateur DCA")
                                col_dca1, col_dca2 = st.columns(2)
                                mensualite = col_dca1.slider("Investissement mensuel (€)", 50, 1000, 150, 50, key="dca1")
                                annees = col_dca2.slider("Durée du backtest (Années)", 1, 15, 5, 1, key="dca2")
                                
                                hist_dca = d['ticker_obj'].history(period=f"{annees}y")
                                if not hist_dca.empty:
                                    hist_dca['Close_EUR'] = hist_dca['Close'] * d['taux_fx']
                                    monthly = hist_dca['Close_EUR'].resample('ME').last().dropna()
                                    invested_capital, portfolio_value = [], []
                                    total_shares, total_invested = 0, 0
                                    
                                    for price in monthly:
                                        shares_bought = mensualite / price
                                        total_shares += shares_bought
                                        total_invested += mensualite
                                        invested_capital.append(total_invested)
                                        portfolio_value.append(total_shares * price)
                                    
                                    fig_dca = go.Figure()
                                    fig_dca.add_trace(go.Scatter(x=monthly.index, y=invested_capital, mode='lines', name='Capital Investi (€)', line=dict(color='gray', dash='dash')))
                                    fig_dca.add_trace(go.Scatter(x=monthly.index, y=portfolio_value, mode='lines', name='Valeur du Portefeuille (€)', fill='tonexty', line=dict(color='green')))
                                    fig_dca.update_layout(title=f"Croissance DCA sur {d['nom']}", yaxis_title="Euros (€)", template="plotly_dark")
                                    st.plotly_chart(fig_dca, use_container_width=True)
                                    
                                    final_val = portfolio_value[-1]
                                    st.success(f"Bilan : Total investi = **{total_invested:,.0f} €** | Valeur finale = **{final_val:,.0f} €** (Perf: **{((final_val/total_invested)-1)*100:.2f}%**)")

                            # --- TAB 4 : ACTUALITÉS ---
                            with tab4:
                                st.subheader("📰 Fil d'actualité financier (Flux Yahoo)")
                                news = d['ticker_obj'].news
                                if news:
                                    for article in news[:5]:
                                        titre = article.get('title', 'Titre indisponible')
                                        lien = article.get('link', '#')
                                        editeur = article.get('publisher', 'Inconnu')
                                        ts = article.get('providerPublishTime')
                                        date_pub = datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M') if ts else 'Date inconnue'
                                        
                                        st.markdown(f"🔗 **[{titre}]({lien})**")
                                        st.caption(f"Publié par {editeur} le {date_pub}")
                                        st.write("---")
                                else:
                                    st.info("Aucune actualité récente trouvée pour ce titre.")
            except Exception as e:
                st.error(f"Erreur critique lors de l'analyse : {e}")

# =========================================================
# MODE COMPARATEUR PRO (AVEC EXPORT CSV)
# =========================================================
else:
    st.header("🏛️ Comparateur Multitâche Pro")
    type_comparaison = st.radio("Sélectionnez le type d'actifs à comparer :", ["🏢 Actions", "📊 ETF"])
    
    if type_comparaison == "🏢 Actions":
        tickers_input = st.text_input("Entrez les symboles des actions séparés par des virgules (ex: AAPL, MSFT, RMS.PA, NVDA) :", value="AAPL, MSFT, OR.PA")
        liste_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        
        if st.button("Lancer la Comparaison"):
            resultats = []
            with st.spinner("Analyse et conversion en Euros en cours..."):
                for t in liste_tickers:
                    d = extraire_donnees_action(t)
                    if d:
                        resultats.append({
                            "Ticker": t, "Nom": d['nom'], "Score (/100)": d['score'],
                            "Prix (€)": round(d['prix'], 2), "Cap. (M€)": round(d['cap'], 0),
                            "Dette/EBITDA": round(d['ratio_d_e'], 2) if d['ratio_d_e'] != float('inf') else "N/A",
                            "Marge Nette (%)": round(d['marge_net'], 2), "ROE (%)": round(d['roe'], 2),
                            "PER (x)": round(d['per'], 2) if d['per'] else "N/A", "Prix Graham (€)": round(d['p_graham'], 2) if d['p_graham'] > 0 else "N/A",
                            "Div Yield (%)": round(d['div_yield'], 2), "Consensus": d['reco'].upper()
                        })
            
            if resultats:
                df = pd.DataFrame(resultats)
                st.dataframe(df.set_index("Ticker").style.background_gradient(subset=['Score (/100)'], cmap='Greens'), use_container_width=True)
                
                # BOUTON EXPORT CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Télécharger le rapport en CSV", data=csv, file_name="comparaison_actions.csv", mime="text/csv")
                
                # GRAPHIQUE COMPARATIF SCORES
                fig_comp = go.Figure(go.Bar(x=df["Ticker"], y=df["Score (/100)"], marker_color='MediumSeaGreen'))
                fig_comp.update_layout(title="Classement par Score de Qualité", yaxis_title="Score / 100", template="plotly_dark")
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.error("Aucune donnée récupérée.")
                
    else:
        tickers_input = st.text_input("Entrez les symboles des ETF séparés par des virgules (ex: SPY, CW8.PA) :", value="SPY, CW8.PA, ESE.PA")
        liste_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        
        if st.button("Lancer la Comparaison"):
            resultats = []
            with st.spinner("Analyse et conversion en cours..."):
                for t in liste_tickers:
                    d = extraire_donnees_etf(t)
                    if d:
                        resultats.append({
                            "Ticker": t, "Nom": d['nom'], "Score (/100)": d['score'],
                            "Prix (€)": round(d['prix'], 2), "Frais (TER %)": round(d['frais'], 2) if d['frais'] > 0 else "N/A", 
                            "Encours (M€)": round(d['encours'], 1) if d['encours'] > 0 else "N/A", 
                            "Rendement (%)": round(d['rendement'], 2) if d['rendement'] > 0 else "N/A"
                        })
            
            if resultats:
                df = pd.DataFrame(resultats)
                st.dataframe(df.set_index("Ticker").style.background_gradient(subset=['Score (/100)'], cmap='Greens'), use_container_width=True)
                
                # BOUTON EXPORT CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Télécharger le rapport en CSV", data=csv, file_name="comparaison_etf.csv", mime="text/csv")
                
                # GRAPHIQUE COMPARATIF SCORES
                fig_etf = go.Figure(go.Bar(x=df["Ticker"], y=df["Score (/100)"], marker_color='CornflowerBlue'))
                fig_etf.update_layout(title="Classement des ETF par Score de Qualité", yaxis_title="Score / 100", template="plotly_dark")
                st.plotly_chart(fig_etf, use_container_width=True)
            else:
                st.error("Aucune donnée récupérée.")
