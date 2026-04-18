# Setup script for sentiment-analysis skill on Windows
# Run from the repo root: .\skills\sentiment-analysis\scripts\setup.ps1

Write-Host "Setting up sentiment-analysis dependencies..." -ForegroundColor Cyan

# 1. Install Python packages
Write-Host "`n[1/3] Installing transformers and torch..." -ForegroundColor Yellow
pip install transformers torch
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip install failed. Make sure Python is installed and on PATH." -ForegroundColor Red
    exit 1
}

# 2. Add Python user Scripts directory to PATH (fixes pip warnings)
$pythonScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))" 2>$null
if ($pythonScripts -and (Test-Path $pythonScripts)) {
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$pythonScripts*") {
        Write-Host "`n[2/3] Adding Python Scripts to user PATH: $pythonScripts" -ForegroundColor Yellow
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$pythonScripts", "User")
        $env:PATH = "$env:PATH;$pythonScripts"
        Write-Host "    Done. Restart PowerShell for PATH change to take full effect." -ForegroundColor Green
    } else {
        Write-Host "`n[2/3] Python Scripts already on PATH. Skipping." -ForegroundColor Green
    }
} else {
    Write-Host "`n[2/3] Could not detect Python Scripts path. Skipping." -ForegroundColor DarkYellow
}

# 3. Verify install and run a quick smoke test
Write-Host "`n[3/3] Running smoke test..." -ForegroundColor Yellow
$scriptPath = Join-Path $PSScriptRoot "analyze_sentiment.py"
python $scriptPath --backend transformers --text "Setup complete, everything works great!"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Smoke test failed." -ForegroundColor Red
    exit 1
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Usage: python skills\sentiment-analysis\scripts\analyze_sentiment.py --text `"your text here`"" -ForegroundColor Cyan
