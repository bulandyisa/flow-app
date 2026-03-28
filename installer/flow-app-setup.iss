; ============================================
; Flow App — Inno Setup Script
; ============================================

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#ifndef BuildDir
  #define BuildDir ".\build"
#endif

#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
AppName=Flow App
AppVersion={#AppVersion}
AppPublisher=GenVid
DefaultDirName={localappdata}\FlowApp
DisableProgramGroupPage=yes
DisableDirPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=FlowApp-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
SetupIconFile={#BuildDir}\FlowApp.ico
UninstallDisplayIcon={app}\FlowApp.ico
WizardStyle=modern
WizardSizePercent=120

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
russian.WelcomeLabel2=Flow App — production tool for animated films via Google Flow.%n%nThe installer will set up everything needed on your computer.
russian.FinishedLabel=Installation complete. Click Finish to launch the application.

[Files]
; Runtimes
Source: "{#BuildDir}\node\*"; DestDir: "{app}\node"; Flags: recursesubdirs
Source: "{#BuildDir}\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs
Source: "{#BuildDir}\chromium\*"; DestDir: "{app}\chromium"; Flags: recursesubdirs
Source: "{#BuildDir}\ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: recursesubdirs

; Application code
Source: "{#BuildDir}\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs

; Launcher, VBS wrapper, update checker
Source: "{#BuildDir}\launcher.bat"; DestDir: "{app}"
Source: "{#BuildDir}\FlowApp.vbs"; DestDir: "{app}"
Source: "{#BuildDir}\update-checker.js"; DestDir: "{app}"

; Icon
Source: "{#BuildDir}\FlowApp.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\data"
Name: "{app}\data\projects"
Name: "{app}\data\sessions"

[Icons]
; Desktop and Start Menu shortcuts point to VBS (no console window)
Name: "{userdesktop}\Flow App"; Filename: "wscript.exe"; Parameters: """{app}\FlowApp.vbs"""; IconFilename: "{app}\FlowApp.ico"; Comment: "Flow App"
Name: "{userprograms}\Flow App\Flow App"; Filename: "wscript.exe"; Parameters: """{app}\FlowApp.vbs"""; IconFilename: "{app}\FlowApp.ico"
Name: "{userprograms}\Flow App\Uninstall Flow App"; Filename: "{uninstallexe}"

[Run]
; Launch after install via VBS (no console window)
Filename: "wscript.exe"; Parameters: """{app}\FlowApp.vbs"""; Description: "Launch Flow App"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_update_temp"
Type: filesandordirs; Name: "{app}\app.old"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    EnvPath := ExpandConstant('{app}\app\.env');
    if not FileExists(EnvPath) then
    begin
      SaveStringToFile(EnvPath,
        'NODE_ENV=production' + #13#10 +
        'PORT=3000' + #13#10 +
        'DATA_DIR=' + ExpandConstant('{app}\data') + #13#10,
        False);
    end;
  end;
end;
