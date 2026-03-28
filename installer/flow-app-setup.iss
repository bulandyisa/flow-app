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
WizardStyle=modern
WizardSizePercent=120

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
russian.WelcomeLabel2=Программа установит Flow App на ваш компьютер.%n%nFlow App — приложение для производства мультфильмов через Google Flow.
russian.FinishedLabel=Установка завершена. Нажмите «Готово» для запуска приложения.

[Files]
; Рантаймы
Source: "{#BuildDir}\node\*"; DestDir: "{app}\node"; Flags: recursesubdirs
Source: "{#BuildDir}\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs
Source: "{#BuildDir}\chromium\*"; DestDir: "{app}\chromium"; Flags: recursesubdirs
Source: "{#BuildDir}\ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: recursesubdirs

; Код приложения
Source: "{#BuildDir}\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs

; Лаунчер и утилиты
Source: "{#BuildDir}\launcher.bat"; DestDir: "{app}"
Source: "{#BuildDir}\update-checker.js"; DestDir: "{app}"

; Иконка (опционально)
Source: "{#BuildDir}\FlowApp.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
Name: "{app}\data"
Name: "{app}\data\projects"
Name: "{app}\data\sessions"

[Icons]
Name: "{userdesktop}\Flow App"; Filename: "{app}\launcher.bat"; Comment: "Запустить Flow App"
Name: "{userprograms}\Flow App\Flow App"; Filename: "{app}\launcher.bat"
Name: "{userprograms}\Flow App\Удалить Flow App"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\launcher.bat"; Description: "Запустить Flow App"; Flags: postinstall nowait skipifsilent

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
