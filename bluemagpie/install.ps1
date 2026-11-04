# 青鳥 · 台灣藍鵲 BlueMagpie — Windows 一鍵安裝（PowerShell，需 Docker Desktop）
param([string]$Role = "primary")
Set-Location $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host "請先安裝 Docker Desktop：https://www.docker.com/products/docker-desktop/" -ForegroundColor Red; exit 1 }
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  $pw = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 16 | ForEach-Object {[char]$_})
  (Get-Content .env) -replace '^ADMIN_PASSWORD=.*', "ADMIN_PASSWORD=$pw" | Set-Content .env
  Write-Host "已產生 .env（後台密碼：$pw）"
}
if ($Role -eq "standby") { (Get-Content .env) -replace '^COMPOSE_PROFILES=.*', 'COMPOSE_PROFILES=standby' | Set-Content .env }
foreach ($d in "config/homeassistant/packages","config/homeassistant/www/hermes","config/mosquitto","config/zigbee2mqtt","config/hermes","data","backups") { New-Item -ItemType Directory -Force -Path $d | Out-Null }
if (-not (Test-Path config/mosquitto/mosquitto.conf)) { Copy-Item provision/mosquitto/mosquitto.conf config/mosquitto/ }
if (-not (Test-Path config/mosquitto/passwd)) { New-Item config/mosquitto/passwd -ItemType File | Out-Null }
if (-not (Test-Path config/hermes/hermes.yaml)) { Copy-Item provision/hermes/* config/hermes/ -Recurse }
docker compose up -d --build
$port = (Get-Content .env | Select-String '^ADMIN_PORT=').ToString().Split('=')[1]
Write-Host "完成。後台：http://localhost:$port" -ForegroundColor Blue
