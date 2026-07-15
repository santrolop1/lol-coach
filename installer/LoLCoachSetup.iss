; LoLCoachSetup.iss — Script de Inno Setup para LoL Coach
;
; Prerequisito: Inno Setup 6 instalado (https://jrsoftware.org/isdl.php)
;
; Para generar el instalador:
;   iscc installer\LoLCoachSetup.iss
;
; O abrirlo en el IDE de Inno Setup y presionar Compile.

#define AppName        "LoL Coach"
#define AppVersion     "1.0.0-beta.1"
#define AppPublisher   "Santiago"
#define AppURL         "https://github.com/santrolop1/lol-coach"
#define AppExeName     "LoLCoach.exe"
#define AppId          "{{A7B3C4D5-E6F7-8901-ABCD-EF1234567890}"
#define DistDir        "..\dist\LoLCoach"

[Setup]
; Identificador único — NO cambiar entre versiones
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Instalación en Program Files
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}

; El instalador se genera aquí
OutputDir=.
OutputBaseFilename=LoLCoachSetup-{#AppVersion}

; Compresión
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Permisos — solo el usuario actual (no requiere admin salvo si es Program Files)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Icono del instalador
; SetupIconFile=..\assets\icon.ico   ; Descomentar cuando tengas un .ico

; Windows 10+ requerido
MinVersion=10.0

; Información visible en el instalador
WizardStyle=modern
WizardImageFile=compiler:WizModernImage-IS.bmp
WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp

; Mostrar licencia si existe
; LicenseFile=..\LICENSE.txt         ; Descomentar si tienes licencia

; Desinstalador
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon";    Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "startmenuicon";  Description: "Crear acceso directo en Inicio";         GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
; Copiar todo el contenido de dist\LoLCoach\
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Acceso directo en Menú Inicio
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"

; Acceso directo en Escritorio (solo si el usuario lo eligió)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Opción para lanzar la app al terminar la instalación
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Al desinstalar, borrar los archivos generados en tiempo de ejecución
; NOTA: Los datos del usuario en %APPDATA%\LoLCoach\ se conservan intencionalmente.
; Si quieres borrarlos también, descomenta la línea de abajo.
; Type: filesandordirs; Name: "{userappdata}\LoLCoach"
