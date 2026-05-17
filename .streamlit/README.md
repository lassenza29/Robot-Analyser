# 📈 Alpha Terminal Pro v2.0

**Terminal Financier Professionnel | Actions, ETF, Analyse & Simulation**

Un application Streamlit haute performance pour analyse complète d'actions et ETF mondiaux avec conversion EUR automatique, 21 ratios fondamentaux, scoring intelligent et simulateur DCA précis.

---

## 🚀 Démarrage Rapide

### Installation
```bash
pip install -r requirements.txt
```

### Lancer l'App
```bash
streamlit run app.py
```

L'app s'ouvre sur `http://localhost:8501` ✅

---

## 📊 Modules Disponibles

### 1. 🔍 Analyse Action/ETF
- **21 Ratios Fondamentaux** (Valorisation, Rentabilité, Santé, Croissance)
- **Score Fondamental 0-100** intelligent
- **Graphiques Technique** (SMA 50/200, RSI 14)
- **Consensus Analystes** (Objectif cours, Recommandations)
- **Simulateur DCA** intégré
- **Actualités** en temps réel

### 2. 📊 Comparateur Multi-Actifs
- Matrice de comparaison (N tickers)
- Tri automatique par Score
- Export CSV instantané
- Formatage professionnel

### 3. 💰 Simulateur DCA Premium
- Dollar Cost Averaging avec historique réel
- Achats 1er jour ouvré de chaque mois
- Capital Investi vs Valeur Réelle
- Rendement % & Plus-value brute
- Période: 1, 3, 5 ou 10 ans

---

## 📋 Les 21 Ratios Financiers

### A. Valorisation & Prix (8)
1. PER Actuel (Trailing P/E)
2. PER Futur (Forward P/E)
3. Price to Sales (P/S)
4. Price to Book (P/B)
5. EV/EBITDA
6. BPA (EPS) €
7. Valeur Comptable par Action €
8. Prix Théorique Graham

### B. Rentabilité (5)
9. Marge Brute %
10. Marge Opérationnelle %
11. Marge Nette %
12. ROE (Return on Equity) %
13. ROA (Return on Assets) %

### C. Santé Financière (6)
14. Dette Nette M€
15. EBITDA M€
16. Ratio Dette Nette/EBITDA
17. Current Ratio (Liquidité)
18. Quick Ratio (Liquidité Imm.)
19. Debt to Equity %

### D. Croissance & Dividendes (2)
20. Croissance Chiffre d'Affaires %
21. Taux Distribution Dividende %

### E. Consensus & Score
- Objectif de cours
- Nombre d'analystes
- Recommandation globale
- **Score Fondamental 0-100**

---

## 🎯 Score Fondamental

Règles de scoring strictes basées sur seuils institutionnels:

| Critère | Points | Seuil |
|---------|--------|-------|
| PER < 20x | +8 | Valorisation faible |
| P/B < 3x | +8 | Actifs bon marché |
| Prix Graham > Prix Actuel | +9 | Upside potentiel |
| Marge Nette > 12% | +10 | Rentabilité élevée |
| ROE > 15% | +8 | Rendement capitaux |
| ROA > 8% | +7 | Rendement actifs |
| Dette/EBITDA < 2x | +12 | Sain financièrement |
| Cash Positif | +15 | Ultra sain |
| Current Ratio 1.5-3 | +8 | Liquidité OK |
| D/E < 100% | +10 | Levier contrôlé |
| Croissance > 10% | +12 | Croissance rapide |
| Payout 20-70% | +8 | Dividende modéré |

**Score:** 50 (base) + points bonus (max 100)

---

## 🎯 Analyse ETF

Pour les ETF détectés automatiquement:

1. **TER (Frais)** - % annuel
2. **AUM (Encours)** - M€ ou B€
3. **Distribution** - Dist vs Capitalisation
4. **Réplication** - Physique vs Synthétique
5. **PEA** - Éligibilité (probabiliste)

⚠️ **Alerte**: AUM < 100M€ = Risque liquidité

---

## 💱 Conversion Devises

Automatique pour toutes les devises:

| Code | Fallback |
|------|----------|
| USD | 0.92 |
| GBP | 1.17 |
| CHF | 1.04 |
| CAD | 0.68 |
| JPY | 0.0067 |
| AUD | 0.61 |
| CNY | 0.128 |
| INR | 0.011 |

✅ Récupération temps réel via Yahoo Finance + Fallback local

---

## 📊 Graphiques

### Technique
- **Prix** (courbe principal)
- **SMA 50** (moyenne mobile orange)
- **SMA 200** (moyenne mobile rouge)
- **RSI 14** (sous-graphique, seuils 30/70)

### DCA
- **Capital Investi** (linéaire, orange)
- **Valeur Portefeuille** (fluctuante, vert)

---

## 🔒 Robustesse

✅ **Parsing Défensif:**
- `safe_float()` - Gestion None/NaN/erreur
- `safe_pct()` - Formatage % sûr
- `safe_str()` - Conversion string robuste

✅ **Gestion Erreurs:**
- Try/except systématique sur API
- Fallback données manquantes
- Messages d'erreur clairs

✅ **Aucun Crash:**
- N/A gracieux au lieu de crash
- Validations données strictes
- Timeout/retry sur API

---

## 📥 Export CSV

Bouton "Télécharger CSV" pour la matrice de comparaison:

```
Ticker,Prix €,Capitalisation,Score,PER,Marge Nette,Det/EBITDA
AAPL,185.40,2850B,82/100,28.5,25%,Cash Positif
MSFT,415.20,3100B,79/100,32.1,32%,0.8x
...
```

Encodage UTF-8, séparateur virgule ✅

---

## 📝 Exemples de Tickers

### Actions Monde
- 🇺🇸 USA: AAPL, MSFT, NVDA, TSLA, GOOGL
- 🇫🇷 France: LVMH.PA, ASML.AS, SAF.PA, MC.PA
- 🇳🇱 Pays-Bas: ASML.AS
- 🇬🇧 UK: GSK.L, AZN.L, HSBA.L
- 🇪🇺 Europe: SIE.DE, VOW3.DE

### ETF Populaires
- 🌍 World: CW8.PA (Amundi MSCI World), ESE.PA (iShares MSCI World)
- 🇪🇺 Europe: EXS1.L (iShares STOXX Europe 600)
- 🇫🇷 France: CAC.PA (indice CAC 40)
- 🇺🇸 USA: SPY (S&P 500)

---

## ⚙️ Configuration

**Fichier:** `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#0e1117"
font = "sans serif"

[client]
maxUploadSize = 200
```

---

## 🐛 Troubleshooting

| Problème | Solution |
|----------|----------|
| Ticker non trouvé | Vérifiez l'orthographe (ex: LVMH.PA pas LVMH) |
| Pas d'actualités | Normal, API yfinance peut être vide |
| Données manquantes (N/A) | Titre très petit, données pas disponibles |
| Graph technique vide | < 50 données, attendre ou changer période |
| Erreur "Bytes" CSV | Bug résolu, re-téléchargez |

---

## 📈 Données & Limitations

**Source:** Yahoo Finance (yfinance)

**Limitations Connues:**
- Délai 15-20min pour données temps réel (Yahoo)
- Petites caps: données partielles
- Crypto: support limité
- Données historiques: ~10 ans max

---

## 🏆 Qualité Code

✅ **Production Ready**
- Aucun placeholder
- Type hints (Python 3.10+)
- Error handling complet
- Cache LRU pour API

✅ **Performance**
- Cache conversion devises
- Lazy loading données
- Graphiques Plotly optimisés

✅ **Sécurité**
- Aucune injection SQL (yfinance géré)
- Input validation
- CORS non applicable (local)

---

## 📄 Licence

Libre d'utilisation - 2026

---

**Développé avec ❤️ pour traders & analystes | Streamlit + yfinance + Plotly**
