; Saxon Runner - installazione e disinstallazione (Inno Setup 6)
;
;   ISCC /DAppVersion=3.1.0 installer\SaxonRunner.iss
;
; Si aspetta dist\SaxonRunner.exe gia' compilato da PyInstaller.
; Di default installa per l'utente corrente (niente UAC, e l'aggiornamento
; automatico non chiede la password di amministratore); il dialogo iniziale
; permette di installare per tutti gli utenti.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Saxon Runner"
#define AppExe "SaxonRunner.exe"
#define AppUrl "https://saxonrunner.bais.info/"
#define ManualUrl "https://github.com/bdbais/saxon-runner/blob/main/docs/MANUALE.md"

[Setup]
; L'AppId identifica l'installazione: non va mai cambiato, o gli
; aggiornamenti installerebbero una seconda copia.
AppId={{8F3C2A51-6D7E-4B9A-9C1E-2B7D5E4A9F10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Bais
AppPublisherURL={#AppUrl}
AppSupportURL=https://github.com/bdbais/saxon-runner/issues
AppUpdatesURL=https://github.com/bdbais/saxon-runner/releases
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\Saxon Runner
DefaultGroupName=Saxon Runner
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=SaxonRunner-Setup
SetupIconFile=..\assets\SaxonRunner.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Durante l'aggiornamento Saxon Runner si chiude da solo; se fosse ancora
; aperto, il Restart Manager lo chiude invece di fallire.
CloseApplications=force
RestartApplications=no
ChangesAssociations=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
italian.AssocTask=Apri i file .saxcfg con Saxon Runner
english.AssocTask=Open .saxcfg files with Saxon Runner
italian.AssocName=Configurazione Saxon Runner
english.AssocName=Saxon Runner configuration
italian.ManualShortcut=Manuale utente
english.ManualShortcut=User manual
italian.RemoveSettings=Eliminare anche le impostazioni di Saxon Runner (percorsi dei JAR, esecuzioni recenti, impostazioni AI)?%n%nScegli No se pensi di reinstallarlo.
english.RemoveSettings=Also delete Saxon Runner settings (JAR paths, recent runs, AI settings)?%n%nChoose No if you plan to reinstall it.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "assoc"; Description: "{cm:AssocTask}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:ManualShortcut}"; Filename: "{#ManualUrl}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.saxcfg"; ValueType: string; ValueName: ""; ValueData: "SaxonRunner.saxcfg"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\SaxonRunner.saxcfg"; ValueType: string; ValueName: ""; ValueData: "{cm:AssocName}"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\SaxonRunner.saxcfg\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\SaxonRunner.saxcfg\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: assoc

[Run]
; Installazione normale: casella "Avvia Saxon Runner" nell'ultima pagina.
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; Aggiornamento dall'app (setup silenzioso con /RELAUNCH=1): la riapre.
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: ShouldRelaunch

[Code]
function ShouldRelaunch: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:RELAUNCH|0}') = '1');
end;

procedure DeleteSettings;
var
  Home: String;
begin
  Home := ExpandConstant('{%USERPROFILE}');
  DeleteFile(Home + '\.saxon_runner_config.json');
  DeleteFile(Home + '\.saxon_runner_config.json.tmp');
  DeleteFile(Home + '\.saxon_runner_config.json.corrotto');
  DeleteFile(Home + '\.saxon_runner.log');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // In disinstallazione silenziosa le impostazioni restano: nessuno puo'
  // rispondere alla domanda, e cancellare dati senza chiedere e' peggio.
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) and
     FileExists(ExpandConstant('{%USERPROFILE}\.saxon_runner_config.json')) then
  begin
    if MsgBox(CustomMessage('RemoveSettings'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DeleteSettings;
  end;
end;
