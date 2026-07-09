# Checklist de validación manual — Draft Intelligence

Esto no se pudo ejecutar en el entorno donde se desarrolló Sprint 1/2 (sin
Windows, sin cliente de League corriendo). Es el paso pendiente más
importante antes de abrir la beta — ejecutar con el cliente de League real.

Marca cada caso como ✅ / ❌ / ⚠️ y anota el comportamiento exacto si algo
no coincide con "Esperado".

## Preparación

- [ ] Cuenta con historial descargado (mínimo 10 partidas por rol a probar: ADC / TOP / MID)
- [ ] Cliente de League abierto y logueado
- [ ] `streamlit run main.py` corriendo, pestaña **🎯 Draft** abierta

## Casos — nombres de campeón

| Caso | Cómo probarlo | Esperado |
|---|---|---|
| Campeón con apóstrofe (ADC) | Entra a champ select, elige/observa **Kai'Sa** o **Vel'Koz** | Si tienes historial de ese campeón, Draft Score debe mostrar datos reales (no "Sin historial") |
| Campeón renombrado (TOP) | Observa/elige **Wukong** (alias interno `MonkeyKing`) | Mismo criterio: historial real debe cruzar correctamente |
| Nombre con espacio | **Miss Fortune**, **Twisted Fate**, **Xin Zhao** | Debe mostrar el nombre bonito en el tablero y cruzar con tu historial guardado |

## Casos — bans y picks

| Caso | Cómo probarlo | Esperado |
|---|---|---|
| Ban propio | Banea un campeón de tu pool con buen historial | No debe aparecer en RECOMENDADO ni en EVITAR |
| Ban rival | Observa un ban del equipo contrario que esté en tu pool | Tampoco debe aparecer en las recomendaciones |
| Pick bloqueado por aliado | Un aliado lockea un campeón de tu pool antes que tú | Ese campeón debe desaparecer de tus recomendaciones (League no permite duplicados) |
| Pick bloqueado por rival | Un rival lockea un campeón de tu pool | Igual que el caso anterior |
| Tu propio pick | Lockeas un campeón con historial | Draft Score debe calcularse para TU pick, no excluirte a ti mismo |

## Casos — flujo de partida

| Caso | Cómo probarlo | Esperado |
|---|---|---|
| Autofill | Entra a champ select con un rol autofill (no el que sueles jugar) | Si el rol autofill es JGL/SUP, debe mostrar "Rol no soportado", no crashear. Si es MID, debe mostrar Draft Intelligence (o "Sin historial" si no hay partidas MID) |
| Dodge (alguien se sale) | Alguien abandona el champ select antes del lock-in | La página debe volver a "Buscando partida" sin quedar colgada ni mostrar datos viejos |
| Remake / partida cancelada temprano | Si ocurre, observa la pestaña Draft después | No debe quedar "pegada" en el estado de Champ Select anterior |
| Fin de partida normal | Termina una partida donde Draft Intelligence te dio una recomendación | Debe aparecer el prompt de feedback (⭐ 1-5 + comentario opcional) en la pantalla de "Fin de partida" |

## Casos — historial

| Caso | Cómo probarlo | Esperado |
|---|---|---|
| Cuenta nueva (sin ninguna partida descargada) | Configura una cuenta sin descargar partidas, entra a Draft | Debe mostrar "Sin historial para este rol. Descarga partidas..." — nunca datos de otra cuenta |
| Historial pequeño (1-4 partidas de un rol) | Descarga solo 2-3 partidas de un rol, entra a Coaching | Debe mostrar el aviso de mínimo 5 partidas, no un diagnóstico calculado sobre la muestra chica |
| Historial grande (40-50 partidas) | Descarga el máximo (50) de un rol | La app no debe volverse notablemente lenta al abrir Coaching o Draft (ver nota de rendimiento abajo) |

## Nota de rendimiento a vigilar

Los benchmarks locales (sin red, solo cómputo Python) muestran que
`scorer_v2.analyze_player()` escala de forma no lineal: ~2ms con 20
partidas, ~81ms con 200. Con un historial grande (40-50 partidas por rol,
el máximo real de descarga por sesión) debería seguir siendo imperceptible
(<20ms), pero si notas que **Coaching** tarda visiblemente en cargar,
repórtalo — sería la primera señal real de que ese cuello de botella
importa en la práctica y no solo en el benchmark sintético.

## Errores a vigilar activamente

- Cualquier traceback de Streamlit visible en pantalla (indicaría una
  excepción no capturada — repórtalo con el traceback completo).
- La pestaña Draft quedándose "congelada" sin actualizar durante más de
  unos segundos en Champ Select activo.
- Recomendaciones que no cambian cuando cambian los bans/picks visibles.
