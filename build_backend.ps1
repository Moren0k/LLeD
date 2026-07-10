# Congela el backend Python en dist_backend/servidor/servidor.exe
# Uso:  npm run build:backend   (o)   powershell -ExecutionPolicy Bypass -File build_backend.ps1
$ErrorActionPreference = "Stop"

function Buscar-Python {
  # Evita el alias falso de la Microsoft Store; prueba candidatos reales.
  $candidatos = @(
    "$env:LOCALAPPDATA\Python\bin\python.exe",
    "py",
    "python"
  )
  foreach ($c in $candidatos) {
    try {
      $v = & $c -c "import sys; print(sys.executable)" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v) { return $c }
    } catch {}
  }
  throw "No se encontró un Python real. Instalá Python 3 o ajustá la ruta."
}

$py = Buscar-Python
Write-Host "== Python: $py ==" -ForegroundColor Cyan

Write-Host "== Instalando dependencias + PyInstaller ==" -ForegroundColor Cyan
& $py -m pip install -q --upgrade pyinstaller
& $py -m pip install -q -r requirements.txt

Write-Host "== Limpiando builds previos ==" -ForegroundColor Cyan
if (Test-Path build_pyi) { Remove-Item -Recurse -Force build_pyi }
if (Test-Path "dist_backend\servidor") { Remove-Item -Recurse -Force "dist_backend\servidor" }

Write-Host "== Congelando backend (onedir) ==" -ForegroundColor Cyan
& $py -m PyInstaller servidor.spec --noconfirm --clean --workpath build_pyi --distpath dist_backend

if (-not (Test-Path "dist_backend\servidor\servidor.exe")) {
  throw "Falló el empaquetado: no se generó servidor.exe"
}
Write-Host "== Listo: dist_backend\servidor\servidor.exe ==" -ForegroundColor Green
