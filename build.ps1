# Build locale: test, eseguibile e, se Inno Setup 6 e' installato, installer.
#   .\build.ps1
# La release pubblica la compila la CI (.github/workflows/release.yml).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$version = (Select-String saxon_runner.py -Pattern '^__version__ = "(.+)"').Matches[0].Groups[1].Value
"Saxon Runner $version"

python -m unittest discover -s tests
if ($LASTEXITCODE) { throw 'test falliti' }

python -m PyInstaller --noconfirm --clean SaxonRunner.spec
if ($LASTEXITCODE) { throw 'PyInstaller non riuscito' }

$iscc = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
  & $iscc /Q "/DAppVersion=$version" installer\SaxonRunner.iss
  if ($LASTEXITCODE) { throw 'Inno Setup non riuscito' }
  'Pronti: dist\SaxonRunner.exe e installer\Output\SaxonRunner-Setup.exe'
} else {
  'Pronto: dist\SaxonRunner.exe (Inno Setup 6 non trovato, installer non creato)'
}
