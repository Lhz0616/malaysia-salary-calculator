; Inno Setup Script for Malaysian Salary Calculator
; Compiles a professional Windows installer Setup.exe

#define MyAppName "Malaysian Salary Calculator"
#ifndef MyAppVersion
#define MyAppVersion "0.0.2"
#endif
#define MyAppPublisher "Hong Zhi Lim"
#define MyAppURL "https://github.com/Lhz0616/malaysia-salary-calculator"
#define MyAppExeName "MalaysianSalaryCalculator.exe"

[Setup]
AppId={{C8E1F730-8910-4A9A-B74F-4011E24991FA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=MalaysianSalaryCalculator_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=src\icon\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy all build output files from dist/MalaysianSalaryCalculator
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
