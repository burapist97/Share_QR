<#
  Scanload - Windows derleme betiği
  ----------------------------------
  1) İkonları üretir
  2) PyInstaller ile build\dist\Scanload\Scanload.exe oluşturur ve kendini test eder
  3) MSIX paketi oluşturur: build\Scanload_<sürüm>_x64.msix   (Store'a yüklenecek dosya)
  4) Taşınabilir zip: build\Scanload_<sürüm>_portable.zip

  Gerekenler: Python 3.12, Windows 10/11 SDK (makeappx, makepri, signtool)

  Store için (değerleri Partner Center > Ürün kimliği sayfasından alın):
    .\build.ps1 -Version 1.0.0.0 -IdentityName "12345Ad.Scanload" -Publisher "CN=XXXXXXXX-...." -PublisherDisplayName "Adınız"

  Yerel deneme (kendinden imzalı sertifika ile imzalar):
    .\build.ps1 -Sign
#>
param(
  [string]$Version = "1.1.0.0",
  [string]$IdentityName = "Scanload.Dev",
  [string]$Publisher = "CN=ScanloadDev",
  [string]$PublisherDisplayName = "Scanload",
  [string]$DisplayName = "Scanload",
  [switch]$Sign,
  [switch]$SkipInstall
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$root = $PSScriptRoot
$build = Join-Path $root "build"

if ($Version -notmatch '^\d+\.\d+\.\d+\.0$') { throw "Sürüm X.Y.Z.0 biçiminde olmalı (Store son haneyi 0 ister): $Version" }

Write-Host "==> Bağımlılıklar" -ForegroundColor Cyan
if (-not $SkipInstall) { python -m pip install --disable-pip-version-check -q -r requirements-build.txt }

Write-Host "==> İkonlar" -ForegroundColor Cyan
python tools/make_icons.py

Write-Host "==> PyInstaller" -ForegroundColor Cyan
if (Test-Path $build) { Remove-Item $build -Recurse -Force }
python -m PyInstaller --noconfirm --clean --windowed `
  --name Scanload `
  --icon "$root\app\assets\app.ico" `
  --add-data "$root\app\ui;ui" `
  --add-data "$root\app\assets;assets" `
  --add-data "$root\app\i18n.json;." `
  --hidden-import pystray._win32 `
  --collect-submodules winrt `
  --distpath "$build\dist" --workpath "$build\work" --specpath "$build" `
  "$root\app\scanload.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller başarısız" }

$exe = "$build\dist\Scanload\Scanload.exe"
Write-Host "==> Kendi kendini test" -ForegroundColor Cyan
$p = Start-Process -FilePath $exe -ArgumentList "--selftest" -Wait -PassThru
$log = "$build\dist\Scanload\selftest.log"
if (Test-Path $log) { Get-Content $log; Remove-Item $log }
if ($p.ExitCode -ne 0) { throw "Self-test başarısız (çıkış kodu $($p.ExitCode))" }

Write-Host "==> Taşınabilir zip" -ForegroundColor Cyan
$short = $Version -replace '\.0$', ''
Compress-Archive -Path "$build\dist\Scanload" -DestinationPath "$build\Scanload_${short}_portable.zip" -Force

Write-Host "==> MSIX" -ForegroundColor Cyan
$kit = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending | Select-Object -First 1
if (-not $kit) { throw "Windows SDK bulunamadı (makeappx.exe). Visual Studio Installer'dan 'Windows 10/11 SDK' kurun." }
$bin = $kit.DirectoryName

$layout = "$build\msix"
New-Item -ItemType Directory -Force -Path $layout | Out-Null
Copy-Item "$build\dist\Scanload" "$layout\Scanload" -Recurse
Copy-Item "$root\packaging\Assets" "$layout\Assets" -Recurse
$manifest = Get-Content "$root\packaging\AppxManifest.xml" -Raw -Encoding UTF8
$manifest = $manifest.Replace('{{IDENTITY_NAME}}', $IdentityName).Replace('{{PUBLISHER}}', $Publisher).
  Replace('{{VERSION}}', $Version).Replace('{{PUBLISHER_DISPLAY_NAME}}', [Security.SecurityElement]::Escape($PublisherDisplayName)).
  Replace('{{DISPLAY_NAME}}', [Security.SecurityElement]::Escape($DisplayName))
[IO.File]::WriteAllText("$layout\AppxManifest.xml", $manifest, (New-Object Text.UTF8Encoding $false))

# Ölçeklenmiş ikonlar için kaynak dizini (resources.pri)
Push-Location $layout
& "$bin\makepri.exe" createconfig /cf "$build\priconfig.xml" /dq en-US_tr-TR_es-ES /o | Out-Null
& "$bin\makepri.exe" new /pr $layout /cf "$build\priconfig.xml" /mn "$layout\AppxManifest.xml" /of "$layout\resources.pri" /o
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "makepri başarısız" }
Pop-Location

$msix = "$build\Scanload_${short}_x64.msix"
& "$bin\makeappx.exe" pack /d $layout /p $msix /o
if ($LASTEXITCODE -ne 0) { throw "makeappx başarısız" }

if ($Sign) {
  Write-Host "==> Yerel test için imzalama" -ForegroundColor Cyan
  $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $Publisher } | Select-Object -First 1
  if (-not $cert) {
    $cert = New-SelfSignedCertificate -Type Custom -Subject $Publisher -KeyUsage DigitalSignature `
      -FriendlyName "Scanload test" -CertStoreLocation Cert:\CurrentUser\My `
      -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
  }
  $pwd = ConvertTo-SecureString -String "qrpaylas" -Force -AsPlainText
  Export-PfxCertificate -Cert $cert -FilePath "$build\test.pfx" -Password $pwd | Out-Null
  Export-Certificate -Cert $cert -FilePath "$build\test.cer" | Out-Null
  & "$bin\signtool.exe" sign /fd SHA256 /f "$build\test.pfx" /p qrpaylas $msix
  if ($LASTEXITCODE -ne 0) { throw "signtool başarısız" }
  Write-Host ""
  Write-Host "Kurmak için (bir kerelik, yönetici PowerShell):" -ForegroundColor Yellow
  Write-Host "  Import-Certificate -FilePath `"$build\test.cer`" -CertStoreLocation Cert:\LocalMachine\TrustedPeople"
  Write-Host "Sonra .msix dosyasına çift tıklayın."
}

Write-Host ""
Write-Host "Hazır:" -ForegroundColor Green
Get-ChildItem "$build\*.msix", "$build\*.zip" | ForEach-Object { Write-Host "  $($_.FullName)  ($([math]::Round($_.Length/1MB,1)) MB)" }
