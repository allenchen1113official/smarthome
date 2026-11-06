#!/bin/sh
# 青鳥 Magpie LB — HAProxy + keepalived 一鍵安裝（Alpine 或 Debian/Ubuntu）
# 用法（兩台 LB 節點各跑一次，只有 PRIORITY 不同）：
#   VIP=192.168.0.88 NODE_A=192.168.0.18 NODE_B=192.168.0.28 PRIORITY=150 IFACE=eth0 sh install-lb.sh   # Mac mini 側 LB VM
#   VIP=192.168.0.88 NODE_A=192.168.0.18 NODE_B=192.168.0.28 PRIORITY=100 IFACE=enp1s0 sh install-lb.sh # HA Black
set -e
: "${VIP:?VIP 必填}"; : "${NODE_A:?NODE_A 主節點 IP 必填}"; : "${NODE_B:?NODE_B 副節點 IP 必填}"; : "${PRIORITY:=100}"; : "${IFACE:=eth0}"; : "${VRID:=51}"; : "${PASS:=magpie51}"
DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v apk >/dev/null; then apk add --no-cache haproxy keepalived curl; RC="rc-update add"; SVC="rc-service";
elif command -v apt-get >/dev/null; then apt-get update -q && apt-get install -y -q haproxy keepalived curl; RC="systemctl enable"; SVC="systemctl";
else echo "只支援 Alpine / Debian 系"; exit 1; fi

# 允許綁定尚未持有的 VIP（備機也預先 bind）
sysctl -w net.ipv4.ip_nonlocal_bind=1 >/dev/null; grep -q ip_nonlocal_bind /etc/sysctl.conf 2>/dev/null || echo "net.ipv4.ip_nonlocal_bind=1" >> /etc/sysctl.conf

sed -e "s/__VIP__/$VIP/g" -e "s/__NODE_A__/$NODE_A/g" -e "s/__NODE_B__/$NODE_B/g" "$DIR/haproxy.cfg" > /etc/haproxy/haproxy.cfg
sed -e "s/__VIP__/$VIP/g" -e "s/__PRIORITY__/$PRIORITY/g" -e "s/__IFACE__/$IFACE/g" -e "s/__VRID__/$VRID/g" -e "s/__PASS__/$PASS/g" "$DIR/keepalived.conf" > /etc/keepalived/keepalived.conf
install -m 755 "$DIR/check_haproxy.sh" /usr/local/bin/check_haproxy.sh

haproxy -c -f /etc/haproxy/haproxy.cfg
if [ "$RC" = "rc-update add" ]; then rc-update add haproxy default; rc-update add keepalived default; rc-service haproxy restart; rc-service keepalived restart;
else systemctl enable haproxy keepalived; systemctl restart haproxy keepalived; fi
echo "完成：VIP $VIP（priority $PRIORITY）。HAProxy 統計頁 http://$(hostname -i 2>/dev/null | awk '{print $1}'):8404/stats"
