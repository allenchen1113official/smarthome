#!/bin/sh
# keepalived 追蹤：HAProxy 行程在且統計頁可回應
pidof haproxy >/dev/null 2>&1 || exit 1
curl -fs -m 1 http://127.0.0.1:8404/stats >/dev/null || exit 1
exit 0
