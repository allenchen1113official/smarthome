#!/usr/bin/env bash
# 青鳥 · 台灣藍鵲 BlueMagpie — 一鍵安裝（Linux / macOS）
#   bash install.sh            主節點
#   bash install.sh standby    副節點（只跑後台 + MQTT，等待接手）
set -euo pipefail
cd "$(dirname "$0")"
ROLE="${1:-primary}"
B="\033[1;34m"; R="\033[1;31m"; N="\033[0m"
echo -e "${B}🐦 青鳥 · 台灣藍鵲 BlueMagpie 安裝程式（${ROLE}）${N}"

# 1) Docker
if ! command -v docker >/dev/null 2>&1; then
  case "$(uname -s)" in
    Linux)  echo "安裝 Docker Engine…"; curl -fsSL https://get.docker.com | sh; sudo usermod -aG docker "$USER" || true ;;
    Darwin) echo -e "${R}請先安裝 Docker Desktop for Mac（https://www.docker.com/products/docker-desktop/），裝好後重新執行本腳本。${N}"; exit 1 ;;
  esac
fi
docker compose version >/dev/null 2>&1 || { echo -e "${R}需要 docker compose v2${N}"; exit 1; }

# 2) .env
if [ ! -f .env ]; then
  cp .env.example .env
  PW=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)
  sed -i.bak "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=${PW}/" .env && rm -f .env.bak
  echo "已產生 .env（後台密碼：${PW}）"
fi
if [ "$ROLE" = "standby" ]; then
  sed -i.bak "s/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=standby/" .env && rm -f .env.bak
elif [ "$(uname -s)" = "Darwin" ]; then
  # macOS：Ollama 用主機原生（Metal），容器版不啟動
  sed -i.bak "s/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=primary/" .env && rm -f .env.bak
  command -v ollama >/dev/null 2>&1 || echo "提示：macOS 建議 brew install ollama && ollama pull qwen3:8b && pip install wyoming-mlx-whisper（後台 Ollama 來源選「主機」）"
fi

# 3) 目錄與初始設定（後台「套用」會重新產生）
mkdir -p config/bot data/bot config/homeassistant/packages config/homeassistant/www/hermes config/mosquitto config/zigbee2mqtt config/hermes data backups
[ -f config/mosquitto/mosquitto.conf ] || cp provision/mosquitto/mosquitto.conf config/mosquitto/
[ -f config/mosquitto/passwd ] || touch config/mosquitto/passwd
[ -f config/hermes/hermes.yaml ] || cp -R provision/hermes/. config/hermes/

# 4) 啟動
COMPOSE_FILES="-f docker-compose.yml"
[ "$(uname -s)" = "Linux" ] && COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.host.yml"
docker compose $COMPOSE_FILES --profile primary --profile ollama up -d --build
if [ "$ROLE" = "standby" ]; then
  docker compose $COMPOSE_FILES stop homeassistant zigbee2mqtt hermes bot ollama   # 副節點：容器存在但停止，接手時由後台啟動
elif [ "$(uname -s)" = "Darwin" ]; then
  docker compose $COMPOSE_FILES stop ollama                                    # macOS 用主機原生 Ollama
fi
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1)
echo -e "${B}完成。後台：http://${IP}:$(grep ^ADMIN_PORT .env | cut -d= -f2)   Home Assistant：http://${IP}:$(grep ^HA_PORT .env | cut -d= -f2)${N}"
echo "下一步：打開後台 → 依序填「網站 / Home Assistant / MQTT / Zigbee / 語音 / Hermes」→ 套用。"
