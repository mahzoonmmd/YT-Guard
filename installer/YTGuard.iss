; Inno Setup script for YT Guard.
; Build:  1) run build_exe.bat (creates dist\YTGuard)   2) compile this file with Inno Setup 6 (or run build_installer.bat)
; Prerequisites (FFmpeg, VC++ Runtime) are NOT bundled: the app offers to download/install them on its first launch.

#define AppName "YT Guard"
#define AppVersion "1.0.0"
#define AppPublisher "Mohammadali Mahzoon"
#define AppURL "https://github.com/mahzoonmmd/YT-Guard"
#define AppExe "YTGuard.exe"

[Setup]
AppId={{8F4C6E0A-5B1D-4C77-9A52-0A1B2C3D4E5F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\YTGuard
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=YTGuard-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\YTGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; The app's first screen is the prerequisites installer (FFmpeg, VC++ Runtime) with a live checklist and progress.
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Downloaded prerequisites and settings live in %APPDATA%\YTGuard and are kept (user data); remove manually if wanted.
Type: filesandordirs; Name: "{app}"
