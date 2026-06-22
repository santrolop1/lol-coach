# LoL Coach

Personal performance analyzer for League of Legends. Tracks your matches, calculates scores across farm, survival, and combat, and gives you concrete weekly improvement tips.

Built for ADC and TOP players in Gold–Plat elo.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red)
![SQLite](https://img.shields.io/badge/SQLite-local-green)

---

## Features

- **Match history** — Download your last 5–50 ranked or normal games directly from Riot API
- **Performance scoring** — Farm Score, Survival Score, Fight Score, and Overall Score (0–100)
- **Role-aware benchmarks** — Separate calibration for ADC and TOP
- **Recommendations** — Detects weaknesses and gives one concrete priority tip per week
- **Trend chart** — Visual progression of your Overall Score over time
- **Fully local** — All data stored on your machine in SQLite, nothing sent to third parties

---

## Requirements

- Python 3.10 or higher
- A Riot Games Developer API Key → [developer.riotgames.com](https://developer.riotgames.com)

> **Note:** Developer API Keys expire every 24 hours. You will need to regenerate yours daily.

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/lol-coach.git
cd lol-coach

# 2. Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run main.py
```

The app opens at `http://localhost:8501`.

---

## First-time configuration

1. Go to **⚙️ Configuración**
2. Paste your Riot Developer API Key
3. Enter your Riot ID (Name + Tag, e.g. `YourName` / `LA1`)
4. Select your server region
5. Click **💾 Guardar configuración**
6. Click **Probar API Key y buscar cuenta** to verify your account is found

---

## Downloading matches

1. Go to **🎮 Partidas**
2. Select how many matches to download (5–50)
3. Select queue type:
   - **Ranked Solo/Duo** — recommended for serious analysis
   - **Ranked Flex**
   - **Normal Draft**
   - **Todas** — all queues
4. Click **🔄 Descargar partidas**

---

## Viewing your analysis

1. Go to **📊 Análisis**
2. Filter by role (ADC / TOP) and number of recent games
3. Review your average scores, trend chart, weaknesses, strengths, and weekly tip

---

## Scoring system

All scores range from **0 to 100**.

| Score | What it measures | ADC benchmark (bad → good) |
|---|---|---|
| Farm Score | CS per minute | 4.5 → 7.5 CS/min |
| Survival Score | Deaths + KDA | 7 deaths → 1 death, KDA 1.0 → 4.0 |
| Fight Score | Damage per minute + KDA | 350 → 900 dmg/min |
| Overall Score | Weighted average | Farm 35% + Survival 30% + Fight 35% |

Benchmarks are calibrated for **Gold / Platinum** elo.

---

## Project structure

```
lol-coach/
├── main.py              # Streamlit entry point and navigation
├── db.py                # SQLite storage layer
├── riot_api.py          # Riot Games API client (HTTP + cache)
├── parser.py            # Converts raw Riot JSON to internal MatchData
├── scorer.py            # Scoring engine (0–100)
├── recommendations.py   # Rule-based recommendation system
├── requirements.txt
├── data/
│   └── .gitkeep         # Placeholder — DB and cache created at runtime
└── ui/
    ├── config.py        # Configuration page
    ├── matches.py       # Match download and history page
    └── analysis.py      # Analysis, charts, and recommendations page
```

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Charts | Plotly |
| Storage | SQLite (local) |
| API | Riot Games Match v5, Account v1, League v4 |
| Language | Python 3.10+ |

---

## Important notes

- This app uses a **Riot Games Developer API Key** which expires every 24 hours. It is not intended for production deployment.
- Match data is cached locally in `data/raw/` to minimize API calls.
- Your API Key is stored locally in `data/lol_coach.db` — never share this file.
- Analysis currently supports **ADC** and **TOP** roles only.

---

## License

MIT
