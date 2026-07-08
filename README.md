# LoL Coach

Entrenador personal de League of Legends basado en tu historial real.
Analiza tus partidas, detecta tus problemas concretos y te da un plan de mejora semanal.
Integración con el cliente de LoL para recomendaciones en tiempo real durante el Draft.

Diseñado para jugadores de **ADC, TOP y MID** en elo Gold–Platino.

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
- **Datos avanzados** — Benchmarks por rol (ADC / TOP / MID) contra percentiles de tu historial

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
5. Haz clic en **→ Guardar y verificar cuenta** (un solo botón: guarda y verifica en el mismo paso)

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

| Rol | Dimensión 1 | Dimensión 2 | Dimensión 3 |
|---|---|---|---|
| **ADC** | Economy (CS/min, CS@10, oro/min) | Positioning (muertes, % tiempo muerto, racha viva) | Combat Impact (KP%, % daño del equipo, daño a objetivos/min) |
| **TOP** | Lane Control (CS@10, ventaja CS, oro/min) | Pressure (daño a torres/min, torres, objetivos/min) | Survival (muertes, % tiempo muerto) |
| **MID** | Lane Dominance (CS@10, ventaja CS, oro/min) | Damage Impact (daño/min, % daño del equipo, KP%) | Survival (muertes, % tiempo muerto, racha viva) |

El **Overall Score** es la media de las 3 dimensiones (pesos iguales).

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
- El análisis soporta actualmente **ADC, TOP y MID**. JGL y SUP se implementarán en una versión futura.
- Todos los datos se procesan localmente. Nada se envía a terceros.
- Desde la beta cerrada, la app registra uso básico (pantallas abiertas, recomendaciones mostradas, errores) y feedback opcional en las tablas `event_log` y `feedback` de la misma base SQLite local. No incluye Riot ID, puuid ni API Key — solo se usa para decidir qué mejorar.

---

## 🧪 Beta cerrada

LoL Coach está en fase de validación con un grupo reducido de jugadores reales.
Si estás probando la beta, esto es lo que necesitas saber.

### Inicio rápido para beta testers

1. Sigue **Instalación** y **Configuración inicial** arriba (5 minutos).
2. Descarga tus últimas 20-30 partidas en **🎮 Partidas**.
3. Abre **🧠 Coaching** para tu diagnóstico — necesitas mínimo 5 partidas del mismo rol (ADC, TOP o MID).
4. Con el cliente de League abierto, entra a Champ Select y abre **🎯 Draft** — se actualiza solo, no hace falta refrescar.
5. Al terminar una partida, si Draft Intelligence te dio una recomendación, te va a pedir una valoración de 1 a 5 estrellas. Tómate los 10 segundos — es la señal más útil que nos puedes dar.

### Errores conocidos

- Las recomendaciones de Draft Intelligence **no se han validado todavía contra un cliente de League real** en un entorno de desarrollo — si ves un campeón con historial que aparece como "Sin historial" (especialmente con apóstrofe en el nombre, como Kai'Sa o Vel'Koz), es exactamente el tipo de caso que necesitamos que reportes.
- La API Key de desarrollador expira cada 24h — si dejás de poder descargar partidas de un día para otro, regenera la key en **⚙️ Configuración → Actualizar API Key**.
- El coaching requiere mínimo 5 partidas del mismo rol; con menos, la app te lo dice explícitamente en vez de mostrar un diagnóstico poco confiable.

### Cómo reportar un bug

Cuenta:
1. Qué esperabas que pasara vs. qué pasó.
2. En qué pantalla (Coaching / Partidas / Draft / Configuración).
3. Si fue en Draft: qué campeón, qué rol, si tenías historial previo de ese campeón.
4. Captura de pantalla si es visual.

Todo lo que usa la app para medir uso (pantallas abiertas, recomendaciones mostradas, errores) se guarda **solo en tu base de datos local** (`data/lol_coach.db`, tabla `event_log`) — nunca se envía a ningún servidor. Si reportas un bug, revisar esa tabla localmente puede ayudar a reconstruir qué pasó justo antes del error.

## Licencia

MIT
