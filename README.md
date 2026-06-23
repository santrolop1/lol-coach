# LoL Coach

Entrenador personal de League of Legends basado en tu historial real.
Analiza tus partidas, detecta tus problemas concretos y te da un plan de mejora semanal.
Integración con el cliente de LoL para recomendaciones en tiempo real durante el Draft.

Diseñado para jugadores de **ADC y TOP** en elo Gold–Platino.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.58%2B-red)
![SQLite](https://img.shields.io/badge/SQLite-local-green)

---

## Características

### 🧠 Coaching
- **Scoring V2** — Economy, Positioning, Combat Impact por partida y promedio
- **Coaching engine** — Detecta tu problema principal, causa probable e impacto en LP
- **Plan de entrenamiento** — Acción primaria + secundarias derivadas de tus datos
- **Fortalezas y debilidades** — Basadas en tus métricas reales, sin hardcodes
- **Evolución** — Gráfico de score y muertes por partida con línea de tendencia OLS
- **Datos avanzados** — Benchmarks por rol (ADC / TOP) contra percentiles de tu historial

### 🏆 Champion Intelligence
- **Pool grade** (A–F) — Calculado desde 4 factores: profundidad, rendimiento, consistencia, distribución
- **Clasificación automática** — MAIN / CARRY / COMFORT / TRAP desde tus datos reales
- **Tabla de campeones** — WR, score, tendencia (↑→↓) y flag de peligro por campeón
- **Insights accionables** — Detecta dependencia excesiva, traps y oportunidades de carry

### 🎮 Partidas
- **Descarga** — Últimas 5–50 partidas desde Riot API (Ranked, Normal, Flex)
- **Historial filtrable** — Por rol y campeón con métricas completas
- **Análisis detallado V2** — Sub-scores por dimensión partida a partida

### 🎯 Draft (integración con LCU)
- **Detección automática** del cliente de League of Legends via lockfile
- **Champ Select en tiempo real** — Picks aliados, picks enemigos, bans y timer
- **Draft Intelligence** — Top 3 picks recomendados desde tu historial personal
- **Draft Score** — 0–100 para tu pick actual, desglosado en 4 factores
- **EVITAR** — Lista de traps detectados desde tus datos
- **Alertas** — Picks sin historial, muestra insuficiente, dependencia excesiva
- Auto-refresh cada 750 ms durante Champ Select

---

## Requisitos

- Python 3.10 o superior
- Una API Key de Riot Games → [developer.riotgames.com](https://developer.riotgames.com)
- League of Legends instalado (solo para la función Draft en tiempo real)

> **Nota:** Las API Keys de desarrollo expiran cada 24 horas. Necesitarás regenerar la tuya a diario.

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/santrolop1/lol-coach.git
cd lol-coach

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar la aplicación
streamlit run main.py
```

La app abre en `http://localhost:8501`.

---

## Configuración inicial

1. Ve a **⚙️ Configuración**
2. Pega tu Riot Developer API Key
3. Ingresa tu Riot ID (Nombre + Tag, ej: `TuNombre` / `LA1`)
4. Selecciona tu región
5. Haz clic en **💾 Guardar configuración**
6. Haz clic en **Probar API Key y buscar cuenta** para verificar tu cuenta

---

## Descargar partidas

1. Ve a **🎮 Partidas**
2. Selecciona cuántas partidas descargar (5–50)
3. Selecciona el tipo de cola (Ranked Solo/Duo recomendado)
4. Haz clic en **🔄 Descargar partidas**

Se recomienda tener **al menos 10 partidas por rol** para que el coaching engine funcione de forma confiable.

---

## Sistema de scoring (V2)

Todos los scores van de **0 a 100**.

### Dimensiones por rol

| Dimensión | ADC — métricas | TOP — métricas |
|---|---|---|
| Economy | CS/min, gold/min, CS a los 10 | CS/min, gold/min |
| Positioning | Muertes, KDA, participación | Muertes, KDA, daño recibido |
| Combat Impact | Daño/min, KP%, kills | Daño/min, kill participation |

El **Overall Score** es la media ponderada de las 3 dimensiones.

### Draft Score (pick en Champ Select)

| Factor | Fórmula | Peso |
|---|---|---|
| Familiaridad | `min(30, partidas / 10 × 30)` | 30 pts |
| Rendimiento | `avg_score / 100 × 30` | 30 pts |
| Consistencia | `consistency / 100 × 25` | 25 pts |
| WR personal | `winrate × 15` | 15 pts |

---

## Estructura del proyecto

```
lol-coach/
├── main.py                          # Entry point Streamlit + navegación + CSS
├── db.py                            # Capa SQLite local
├── riot_api.py                      # Cliente Riot Match v5 / Account v1
├── parser.py                        # JSON de Riot → MatchData interno
├── scorer.py                        # Scoring V1 (compatibilidad)
├── scorer_v2.py                     # Scoring V2 multidimensional
├── coaching_engine.py               # Motor de detección de problemas
├── coaching_rules.py                # Reglas por rol (ADC, TOP)
├── requirements.txt
│
├── backend/
│   └── services/
│       ├── champion_analyzer.py     # Pool analysis, clasificación, grade A–F
│       └── draft_advisor.py         # Recomendaciones de draft desde historial
│
├── lcu/
│   ├── client.py                    # Lectura de lockfile + HTTP al cliente LCU
│   ├── models.py                    # Dataclasses: ChampSelectSession, ChampionSlot…
│   └── champ_select.py              # Parser de sesión JSON → modelos tipados
│
├── ui/
│   ├── coaching.py                  # Página 🧠 Coaching (principal)
│   ├── matches.py                   # Página 🎮 Partidas
│   ├── draft.py                     # Página 🎯 Draft (LCU + Draft Intelligence)
│   └── config.py                    # Página ⚙️ Configuración
│
└── data/
    └── lol_coach.db                 # Base de datos SQLite (generada en runtime)
```

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| UI | Streamlit 1.58 |
| Charts | Plotly 6 |
| Storage | SQLite (local) |
| Riot API | Match v5, Account v1, League v4 |
| LCU API | HTTP local + lockfile (no oficial) |
| Lenguaje | Python 3.10+ |

---

## Notas importantes

- La integración con LCU (Draft en tiempo real) usa la API interna del cliente de League, la cual **no es oficial y puede cambiar sin aviso**. Solo se realizan lecturas (GET), sin modificar el cliente.
- Tu API Key de Riot se almacena localmente en `data/lol_coach.db` — no compartas este archivo.
- El análisis soporta actualmente **ADC y TOP**. MID, JGL y SUP se activarán cuando haya suficientes partidas por rol.
- Todos los datos se procesan localmente. Nada se envía a terceros.

---

## Licencia

MIT
