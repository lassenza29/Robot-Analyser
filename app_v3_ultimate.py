import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import math

# Configuration de la page (Mode Pro Ultime)
st.set_page_config(page_title="Analyseur Financier Pro & Comparateur", page_icon="🏛️", layout="wide")

st.title("🏛️ Assenza Analyseur Financier Professionnel ")
st.markdown("Outil d'analyse fondamentale, de visualisation graphique et de comparaison d'actifs (Actions & ETF).")

# --- FONCTIONS DE SÉCURITÉ & DE CALCULS AVANCÉS ---
def get_float(info_dict, key, mult=1.0, default=0.0):
    val = info_dict.get(key)
    if val is None: return default
    try: return float(val) * mult
    except (ValueError, TypeError): return default

def get_str(info_dict, key, default="N/A"):
    val = info_dict.get(key)
    return str(val).strip() if val is not None else default

def extraire_donnees_action(ticker_symbole):
    try:
        ticker = yf.Ticker(ticker_symbole)
        info = ticker.info
        if not info or ('shortName' not in info and 'longName' not in info):
            return None
        
        nom = info.get('longName') or info.get('shortName') or ticker_symbole
        prix = get_float(info, 'currentPrice') or get_float(info, 'regularMarketPrice')
        cap = get_float(info, 'marketCap', 1 / 1_000_000)
        
        # --- CORRECTIF DETTE & TRÉSORERIE ---
        dette_b = get_float(info, 'totalDebt', 1 / 1_000_000)
        treso = get_float(info, 'totalCash', 1 / 1_000_000)
        
        if dette_b == 0:
            dette_b = (get_float(info, 'longTermDebt') + get_float(info, 'shortLongTermDebt')) / 1_000_000
            
        dette_n = dette_b - treso
        ebitda = get_float(info, 'ebitda', 1 / 1_000_000)
        ratio_d_e = dette_n / ebitda if ebitda > 0 else (0.0 if dette_n <= 0 else float('inf'))
        
        ca = get_float(info, 'totalRevenue', 1 / 1_000_000)
        res_expl = get_float(info, 'operatingIncome', 1 / 1_000_000) or get_float(info, 'operatingCashflow', 1 / 1_000_000)
        res_net = get_float(info, 'netIncomeToCommon', 1 / 1_000_000)
        marge_expl = get_float(info, 'operatingMargins', 100.0)
        marge_net = get_float(info, 'profitMargins', 100.0)
        
        actions = get_float(info, 'sharesOutstanding')
        actif_net_a = get_float(info, 'bookValue')
        
        # --- CORRECTIF CAPITAUX PROPRES & ACTIF NET ---
        cp = get_float(info, 'totalStockholderEquity', 1 / 1_000_000)
        if cp == 0 and actif_net_a > 0 and actions > 0:
            cp = (actif_net_a * actions) / 1_000_000
        elif cp > 0 and actif_net_a == 0 and actions > 0:
            actif_net_a = (cp * 1_000_000) / actions

        roe = get_float(info, 'returnOnEquity', 100.0)
        bna = get_float(info, 'trailingEps') or get_float(info, 'forwardEps')
        per = get_float(info, 'trailingPE')
        
        # --- CORRECTIF VALEUR JUSTE DE GRAHAM ---
        produit_graham = 22.5 * bna * actif_net_a
        p_graham = math.sqrt(produit_graham) if produit_graham > 0 else 0.0
        
        return {
            "nom": nom, "prix": prix, "cap": cap, "dette_b": dette_b, "treso": treso,
            "dette_n": dette_n, "ebitda": ebitda, "ratio_d_e": ratio_d_e, "ca": ca,
            "res_expl": res_expl, "res_net": res_net, "marge_expl": marge_expl,
            "marge_net": marge_net, "cp": cp, "roe": roe, "actions": actions,
            "bna": bna, "per": per, "actif_net_a": actif_net_a, "p_graham": p_graham,
            "ticker_obj": ticker
        }
    except Exception:
        return None

def extraire_donnees_etf(ticker_symbole):
    try:
        ticker = yf.Ticker(ticker_symbole)
        info = ticker.info
        if not info or ('shortName' not in info and 'longName' not in info):
            return None
            
        nom = info.get('longName') or info.get('shortName') or ticker_symbole
        frais = get_float(info, 'expenseRatio', 100.0)
        encours = get_float(info, 'totalAssets', 1 / 1_000_000)
        rendement = get_float(info, 'trailingAnnualDividendYield', 100.0) or get_float(info, 'yield', 100.0)
        
        return {
            "nom": nom, "frais": frais, "encours": encours, "rendement": rendement, "ticker_obj": ticker
        }
    except Exception:
        return None

# --- NAVIGATION DE L'APPLICATION ---
onglets = st.sidebar.radio("Navigation 🛠️", ["Analyse Unique", "Comparateur Pro"])

if onglets == "Analyse Unique":
    st.header("🔍 Analyse Individuelle de Titre")
    ticker_symbole = st.text_input("Entrez le symbole (ex: AAPL, RMS.PA, CW8.PA, SPY) :", value="AAPL").upper().strip()
    
    if ticker_symbole:
        with st.spinner("Récupération des données..."):
            try:
                ticker = yf.Ticker(ticker_symbole)
                info = ticker.info
                
                if not info or ('shortName' not in info and 'longName' not in info):
                    st.error("❌ Symbole introuvable. Vérifiez l'extension (ex: .PA pour Paris).")
                else:
                    quote_type = get_str(info, 'quoteType').upper()
                    
                    # ==========================================
                    # MODE ETF UNIQUE
                    # ==========================================
                    if quote_type == "ETF":
                        data = extraire_donnees_etf(ticker_symbole)
                        if data:
                            st.header(f"📊 ETF : {data['nom']} ({ticker_symbole})")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Frais de gestion (TER)", f"{data['frais']:.2f} %")
                            col2.metric("Encours du Fonds", f"{data['encours']:,.1f} M$")
                            col3.metric("Rendement (Dividende)", f"{data['rendement']:.2f} %")
                            
                            st.markdown("### Évaluation des critères :")
                            if 0 < data['frais'] <= 0.30:
                                st.success("🟢 Frais bas (<0.30%). Idéal pour le long terme.")
                            else:
                                st.warning("⚠️ Frais modérés ou élevés (>0.30%).")
                                
                            if data['encours'] >= 100:
                                st.success(f"🟢 Taille critique atteinte ({data['encours']:,.1f} M$). Liquidité optimale, risque de fermeture nul.")
                            else:
                                st.error("🔴 Fonds de petite taille. Risque de liquidité ou de fermeture.")
                    
                    # ==========================================
                    # MODE ACTION UNIQUE
                    # ==========================================
                    else:
                        data = extraire_donnees_action(ticker_symbole)
                        if data:
                            st.header(f"🏢 Action : {data['nom']} ({ticker_symbole})")
                            
                            st.markdown("#### 📊 Ratios Fondamentaux")
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("2. Nom de l'entreprise", data['nom'])
                            c2.metric("3. Prix actuel", f"{data['prix']:,.2f} $")
                            c3.metric("4. Capitalisation", f"{data['cap']:,.0f} M$")
                            c4.metric("17. Actions en circulation", f"{data['actions']:,.0f}" if data['actions'] else "N/A")
                            
                            st.markdown("#### 🛡️ Solvabilité & Bilan")
                            c5, c6, c7, c8 = st.columns(4)
                            c5.metric("5. Dette Brute", f"{data['dette_b']:,.0f} M$")
                            c6.metric("6. Trésorerie", f"{data['treso']:,.0f} M$")
                            c7.metric("7. Dette Nette", f"{data['dette_n']:,.0f} M$")
                            c8.metric("15. Capitaux Propres", f"{data['cp']:,.0f} M$")
                            
                            c9, c10 = st.columns(2)
                            c9.metric("8. EBITDA", f"{data['ebitda']:,.0f} M$")
                            c10.metric("9. Ratio Dette Nette / EBITDA", f"{data['ratio_d_e']:.2f} x" if data['ratio_d_e'] != float('inf') else "EBITDA Négatif")
                            
                            st.markdown("#### 📈 Compte de Résultat & Performance")
                            c11, c12, c13, c14, c15 = st.columns(5)
                            c11.metric("10. Chiffre d'affaires", f"{data['ca']:,.0f} M$")
                            c12.metric("11. Résultat d'Exploit.", f"{data['res_expl']:,.0f} M$")
                            c13.metric("12. Résultat Net", f"{data['res_net']:,.0f} M$")
                            c14.metric("13. Marge d'Exploit.", f"{data['marge_expl']:.2f} %")
                            c15.metric("14. Marge Nette", f"{data['marge_net']:.2f} %")
                            
                            st.markdown("#### 🪙 Valorisation & Multiples")
                            c16, c17, c18, c19 = st.columns(4)
                            c16.metric("16. ROE", f"{data['roe']:.2f} %")
                            c17.metric("18. BNA", f"{data['bna']:.2f} $")
                            c18.metric("19. PER", f"{data['per']:.2f} x" if data['per'] else "N/A")
                            c19.metric("20. Actif Net par Action", f"{data['actif_net_a']:.2f} $")
                            
                            st.markdown("#### ⚖️ Juste Valeur & Verdict")
                            c20, c21 = st.columns(2)
                            c20.metric("21. Prix Juste Graham", f"{data['p_graham']:.2f} $" if data['p_graham'] > 0 else "Non applicable (BNA ou Actif Net Négatif)")
                            
                            is_safe = (data['dette_n'] <= 0) or (data['ratio_d_e'] < 3)
                            is_profitable = (data['marge_expl'] > 8) and (data['roe'] > 10)
                            is_cheap = (data['p_graham'] > 0 and data['prix'] < data['p_graham'])
                            
                            with c21:
                                st.markdown("**1. Critère & Verdict Global :**")
                                if is_safe and is_profitable:
                                    if is_cheap:
                                        st.success("✅ Entreprise Excellente & Sous-évaluée.")
                                    else:
                                        st.warning("⚠️ Entreprise Saine mais prix de marché supérieur à la valeur de Graham.")
                                else:
                                    st.error("❌ Recalée (Dette excessive ou Rentabilité trop faible).")
                                    
                            # ==========================================
                            # AJOUT GRAPHISMES & ÉVOLUTION HISTORIQUE (CORRIGÉ barmode)
                            # ==========================================
                            st.divider()
                            st.header("📈 Évolution Graphique des Métriques")
                            
                            choix_metrique = st.selectbox("Sélectionnez la métrique à analyser historiquement :", 
                                                          ["Chiffre d'affaires & Résultat Net", "Capitaux Propres & Dette Totale"])
                            
                            try:
                                if choix_metrique == "Chiffre d'affaires & Résultat Net":
                                    financials = data['ticker_obj'].financials / 1_000_000
                                    if not financials.empty and "Total Revenue" in financials.index and "Net Income" in financials.index:
                                        annees = financials.columns.strftime('%Y')
                                        fig = go.Figure()
                                        fig.add_trace(go.Bar(x=annees, y=financials.loc["Total Revenue"], name="Chiffre d'affaires (M$)"))
                                        fig.add_trace(go.Bar(x=annees, y=financials.loc["Net Income"], name="Résultat Net (M$)"))
                                        fig.update_layout(barmode='group', title="Évolution des Performances Annuelles", xaxis_title="Année", yaxis_title="Millions $")
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.info("Données financières historiques partielles ou indisponibles pour ce Ticker.")
                                        
                                elif choix_metrique == "Capitaux Propres & Dette Totale":
                                    balance = data['ticker_obj'].balance_sheet / 1_000_000
                                    if not balance.empty:
                                        key_cp = "Stockholders Equity" if "Stockholders Equity" in balance.index else ("Total Equity Gross Minority Interest" if "Total Equity Gross Minority Interest" in balance.index else None)
                                        key_dette = "Total Debt" if "Total Debt" in balance.index else None
                                        
                                        if key_cp:
                                            annees = balance.columns.strftime('%Y')
                                            fig = go.Figure()
                                            fig.add_trace(go.Scatter(x=annees, y=balance.loc[key_cp], mode='lines+markers', name="Capitaux Propres (M$)"))
                                            if key_dette:
                                                fig.add_trace(go.Scatter(x=annees, y=balance.loc[key_dette], mode='lines+markers', name="Dette Totale (M$)"))
                                            fig.update_layout(title="Évolution de la Solvabilité Structurelle (Bilan)", xaxis_title="Année", yaxis_title="Millions $")
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.info("Données de bilan historiques indisponibles pour ce Ticker.")
                            except Exception as e:
                                st.caption(f"Note graphique : Données financières historiques introuvables via l'API ({e}).")
            except Exception as e:
                st.error(f"Erreur lors du chargement : {e}")

# =========================================================
# MODE COMPARATEUR PRO (MULTI-ACTIFS HÉTÉROGÈNES - CORRIGÉ barmode)
# =========================================================
else:
    st.header("🏛️ Comparateur Multitâche Professionnel")
    type_comparaison = st.radio("Sélectionnez le type d'actifs à comparer :", ["🏢 Actions", "📊 ETF"])
    
    if type_comparaison == "🏢 Actions":
        tickers_input = st.text_input("Entrez les symboles des actions séparés par des virgules (ex: AAPL, MSFT, RMS.PA, OR.PA) :", value="AAPL, MSFT")
        liste_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        
        if st.button("Lancer la Comparaison des Ratios"):
            resultats = []
            for t in liste_tickers:
                d = extraire_donnees_action(t)
                if d:
                    resultats.append({
                        "Ticker": t, "Nom": d['nom'], "Prix ($)": round(d['prix'], 2), "Cap. (M$)": round(d['cap'], 0),
                        "Dette Nette (M$)": round(d['dette_n'], 0), "Dette Nette/EBITDA": round(d['ratio_d_e'], 2) if d['ratio_d_e'] != float('inf') else "N/A",
                        "Chiffre d'Aff. (M$)": round(d['ca'], 0), "Marge Expl. (%)": round(d['marge_expl'], 2),
                        "Marge Nette (%)": round(d['marge_net'], 2), "ROE (%)": round(d['roe'], 2), "BNA ($)": round(d['bna'], 2),
                        "PER (x)": round(d['per'], 2) if d['per'] else "N/A", "Prix Graham ($)": round(d['p_graham'], 2) if d['p_graham'] > 0 else "N/A"
                    })
            if resultats:
                df = pd.DataFrame(resultats)
                st.dataframe(df.set_index("Ticker"), use_container_width=True)
                
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Bar(x=df["Ticker"], y=df["Marge Expl. (%)"], name="Marge Exploitation (%)"))
                fig_comp.add_trace(go.Bar(x=df["Ticker"], y=df["Marge Nette (%)"], name="Marge Nette (%)"))
                fig_comp.update_layout(barmode='group', title="Comparaison des Marges de Rentabilité", yaxis_title="%")
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.error("Aucune donnée valide récupérée pour ces tickers d'actions.")
                
    else:
        tickers_input = st.text_input("Entrez les symboles des ETF séparés par des virgules (ex: SPY, EUSA, CW8.PA) :", value="SPY, CW8.PA")
        liste_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        
        if st.button("Lancer la Comparaison des ETF"):
            resultats = []
            for t in liste_tickers:
                d = extraire_donnees_etf(t)
                if d:
                    resultats.append({
                        "Ticker": t, "Nom": d['nom'], "Frais (TER %)": round(d['frais'], 2), 
                        "Encours (M$)": round(d['encours'], 1), "Rendement (%)": round(d['rendement'], 2)
                    })
            if resultats:
                df = pd.DataFrame(resultats)
                st.dataframe(df.set_index("Ticker"), use_container_width=True)
                
                fig_etf = go.Figure(go.Bar(x=df["Ticker"], y=df["Frais (TER %)"], marker_color='indianred'))
                fig_etf.update_layout(title="Comparaison des Frais de Gestion des ETF (Le plus bas est le mieux)", yaxis_title="TER %")
                st.plotly_chart(fig_etf, use_container_width=True)
            else:
                st.error("Aucune donnée valide récupérée pour ces tickers d'ETF.")
