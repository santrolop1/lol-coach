# build.ps1 — Script de build automatizado para LoL Coach (Windows)
#
# Uso:
#   .\build.ps1                    # Build normal
#   .\build.ps1 -Version "1.0.1"   # Build con versión específica
#   .\build.ps1 -SkipClean         # Sin limpiar dist/ previo
#   .\build.ps1 -OpenDist          # Abre dist/ al finalizar
#
# Requisito: Python 3.11+ instalado y en PATH.

param(
    [string] $Version   = "",
    [switch] $SkipClean = $false,
    [switch] $OpenDist  = $false,
    [switch] $Help      = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colores ───────────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n  ► $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "    ✓ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "    ⚠ $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "`n  ✗ $msg" -ForegroundColor Red }

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path
    exit 0
}

Write-Host ""
Write-Host "  ╔══════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "  ║     LoL Coach — Build Script     ║" -ForegroundColor Magenta
Write-Host "  ╚══════════════════════════════════╝" -ForegroundColor Magenta

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# ── Leer versión desde backend/version.py ─────────────────────────────────────
if ($Version -eq "") {
    $versionLine = Select-String -Path "backend\version.py" -Pattern '^VERSION\s*=' | Select-Object -First 1
    if ($versionLine) {
        $Version = ($versionLine.Line -replace '.*"([^"]+)".*', '$1').Trim()
    } else {
        $Version = "1.0.0"
    }
}
Write-Host "`n  Versión: $Version" -ForegroundColor White

# ── 1. Limpiar builds anteriores ──────────────────────────────────────────────
if (-not $SkipClean) {
    Write-Step "Limpiando builds anteriores..."
    foreach ($dir in @("dist", "build")) {
        if (Test-Path $dir) {
            Remove-Item $dir -Recurse -Force
            Write-OK "Eliminado: $dir\"
        }
    }
    # Limpiar __pycache__ para evitar importar código obsoleto
    Get-ChildItem -Recurse -Filter "__pycache__" -Directory |
        Where-Object { $_.FullName -notlike "*node_modules*" -and $_.FullName -notlike "*venv*" } |
        ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
    Write-OK "Limpieza completada"
}

# ── 2. Verificar Python ───────────────────────────────────────────────────────
Write-Step "Verificando Python..."
try {
    $pyVersion = & python --version 2>&1
    Write-OK "$pyVersion"
} catch {
    Write-Fail "Python no encontrado en PATH. Instala Python 3.11+ y agrégualo al PATH."
    exit 1
}

# ── 3. Entorno virtual ────────────────────────────────────────────────────────
Write-Step "Preparando entorno virtual..."
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Warn "Creando entorno virtual..."
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) { Write-Fail "No se pudo crear el entorno virtual"; exit 1 }
    Write-OK "Entorno virtual creado"
} else {
    Write-OK "Entorno virtual existente"
}

& "venv\Scripts\Activate.ps1"

# ── 4. Instalar dependencias ──────────────────────────────────────────────────
Write-Step "Instalando dependencias..."
& pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Fail "Error instalando requirements.txt"; exit 1 }
Write-OK "Dependencias del proyecto OK"

& pip install pyinstaller --quiet
if ($LASTEXITCODE -ne 0) { Write-Fail "Error instalando PyInstaller"; exit 1 }
Write-OK "PyInstaller instalado"

# ── 5. Generar file_version_info.txt (metadata del .exe) ─────────────────────
Write-Step "Generando metadata de versión..."
$vparts = $Version -replace "-.*", "" -split "\."
while ($vparts.Count -lt 4) { $vparts += "0" }
$vStr = ($vparts[0..3] -join ", ")

@"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($vStr),
    prodvers=($vStr),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName',      'LoL Coach'),
        StringStruct('FileDescription',  'LoL Coach - Entrenador para League of Legends'),
        StringStruct('FileVersion',      '$Version'),
        StringStruct('InternalName',     'LoLCoach'),
        StringStruct('LegalCopyright',   'Copyright 2025'),
        StringStruct('OriginalFilename', 'LoLCoach.exe'),
        StringStruct('ProductName',      'LoL Coach'),
        StringStruct('ProductVersion',   '$Version'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)
"@ | Out-File -FilePath "file_version_info.txt" -Encoding UTF8
Write-OK "file_version_info.txt generado"

# ── 6. Ejecutar PyInstaller ───────────────────────────────────────────────────
Write-Step "Ejecutando PyInstaller..."
& pyinstaller LoLCoach.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Fail "PyInstaller falló. Revisa los errores arriba."
    exit 1
}

# ── 7. Verificar output ───────────────────────────────────────────────────────
Write-Step "Verificando output..."
$exePath = "dist\LoLCoach\LoLCoach.exe"
if (-not (Test-Path $exePath)) {
    Write-Fail "No se encontró el ejecutable: $exePath"
    exit 1
}

$exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
$distSize = [math]::Round((Get-ChildItem "dist\LoLCoach" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 0)

Write-OK "Ejecutable generado: $exePath ($exeSize MB)"
Write-OK "Tamaño total dist\: $distSize MB"

# ── 8. Resumen ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║         BUILD EXITOSO ✓          ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Versión:    $Version" -ForegroundColor White
Write-Host "  Output:     dist\LoLCoach\" -ForegroundColor White
Write-Host "  Ejecutable: $exePath" -ForegroundColor White
Write-Host ""
Write-Host "  Próximos pasos:" -ForegroundColor DarkGray
Write-Host "    1. Prueba el ejecutable: .\dist\LoLCoach\LoLCoach.exe" -ForegroundColor DarkGray
Write-Host "    2. Crea el instalador: iscc installer\LoLCoachSetup.iss" -ForegroundColor DarkGray
Write-Host ""

if ($OpenDist) {
    explorer "dist\LoLCoach"
}
