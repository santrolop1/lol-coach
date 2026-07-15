# Diseño del Sistema de Actualización Automática

Estado: DISEÑADO — no implementado.
Implementar en la versión post-beta cuando el ciclo de releases esté establecido.

---

## Recomendación: GitHub Releases + self-updater en Python

### Por qué GitHub Releases

- Gratis, sin servidor propio.
- API pública: `https://api.github.com/repos/santrolop1/lol-coach/releases/latest`
- El instalador `.exe` se adjunta como "asset" en cada release.
- Los beta testers pueden ver el changelog directamente en GitHub.
- Alternativas descartadas:
  - **Squirrel / electron-updater**: para Electron, no para Streamlit.
  - **NSIS auto-updater**: complejo, requiere servidor.
  - **PyUpdater**: no se mantiene activamente desde 2022.

---

## Arquitectura del updater

### Componentes

```
backend/
  updater.py          ← Lógica de detección + descarga
ui/
  about.py            ← Ya tiene la sección "Acerca de" — aquí va el botón
```

### Flujo

```
Al arrancar la app (una vez por sesión):
  1. updater.check_for_update()
     ↓ GET https://api.github.com/repos/.../releases/latest
     ↓ Compara VERSION_TUPLE con tag_name de la respuesta
  2. Si hay versión nueva:
     ↓ Mostrar badge en sidebar: "🔔 Nueva versión disponible"
     ↓ El usuario hace clic → va a "Acerca de"
  3. En "Acerca de":
     ↓ Mostrar changelog de la nueva versión
     ↓ Botón "Descargar e instalar"
     ↓ updater.download_and_install(asset_url)
        → Descarga LoLCoachSetup-X.Y.Z.exe a %TEMP%
        → Lanza el instalador con subprocess.Popen(["installer.exe", "/SILENT"])
        → Cierra la app (st.stop() + sys.exit())
        → El instalador sobreescribe los archivos y crea shortcuts nuevos
```

### API de GitHub (sin autenticación)

```python
import requests
from backend.version import VERSION_TUPLE

RELEASES_URL = "https://api.github.com/repos/santrolop1/lol-coach/releases/latest"

def check_for_update() -> dict | None:
    """
    Retorna dict con {version, changelog, download_url} si hay actualización.
    Retorna None si estamos en la última versión o falla la red (silencioso).
    """
    try:
        r = requests.get(RELEASES_URL, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        tag = data["tag_name"].lstrip("v")
        remote = tuple(int(x) for x in tag.split(".")[:3])
        if remote <= VERSION_TUPLE:
            return None
        asset = next(
            (a for a in data.get("assets", []) if a["name"].endswith(".exe")),
            None,
        )
        return {
            "version":      tag,
            "changelog":    data.get("body", ""),
            "download_url": asset["browser_download_url"] if asset else None,
        }
    except Exception:
        return None  # Fallo silencioso — la app sigue funcionando
```

---

## Requisitos para implementar

1. Subir cada release a GitHub Releases con el instalador como asset.
2. El tag del release debe ser `vX.Y.Z` (ej: `v1.0.1`).
3. El nombre del asset debe terminar en `.exe`.
4. Actualizar `VERSION_TUPLE` en `backend/version.py` antes de cada build.

---

## Checklist de release con auto-updater activo

- [ ] Actualizar `backend/version.py` con la nueva versión
- [ ] Ejecutar `.\build.ps1`
- [ ] Ejecutar `iscc installer\LoLCoachSetup.iss`
- [ ] Crear release en GitHub con tag `vX.Y.Z`
- [ ] Adjuntar `LoLCoachSetup-X.Y.Z.exe` como asset del release
- [ ] Publicar el release (no draft)
- [ ] Verificar que la URL del asset es pública
- [ ] Probar el updater en una instalación existente
