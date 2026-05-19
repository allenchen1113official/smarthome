# SH-001 · Smart Home Core Platform

**Status:** Draft  
**Created:** 2026-05-19  
**Spec-kit phase:** Specification

---

## Problem Statement

住宅缺乏統一的設備管理與自動化平台，導致不同廠牌裝置各自為政、操作分散且無法協同運作。本專案旨在以 Home Assistant 為核心，建立一套可擴展、以 Python 驅動的智慧家庭系統。

---

## User Stories

### US-01 · 設備控制
**As a** 家庭成員，  
**I want** 透過單一介面控制所有智慧設備（燈光、插座、門鎖、空調、窗簾），  
**So that** 我不需要開啟多個 App 或記住不同廠牌的操作方式。

**Acceptance Criteria:**
- [ ] 可從 Home Assistant 儀表板開關任意已配對設備
- [ ] 狀態變更在 2 秒內反映於 UI
- [ ] 支援至少三種協定：MQTT、Zigbee、Wi-Fi（HTTP/REST）

---

### US-02 · 自動化規則
**As a** 使用者，  
**I want** 依時間、感測器數值或裝置狀態觸發自動化動作，  
**So that** 常見情境（回家、離家、就寢、早晨）無需手動操作。

**Acceptance Criteria:**
- [ ] 支援時間排程觸發（cron-like）
- [ ] 支援感測器閾值觸發（溫度、濕度、亮度、人體感應）
- [ ] 支援裝置狀態變更觸發
- [ ] 自動化執行結果記錄至系統日誌
- [ ] 複雜邏輯（多條件、多動作）以 Python 腳本實作

---

### US-03 · 場景模式
**As a** 使用者，  
**I want** 一鍵啟動預設場景（如「電影模式」「用餐模式」「就寢模式」），  
**So that** 多設備的組合設定不需要逐一調整。

**Acceptance Criteria:**
- [ ] 至少支援 6 種預設場景
- [ ] 場景可由使用者透過 UI 自訂
- [ ] 場景啟動後 3 秒內所有設備到達目標狀態

---

### US-04 · 能源監控
**As a** 家庭成員，  
**I want** 查看各設備的即時用電量及歷史趨勢，  
**So that** 我能識別高耗能設備並優化使用習慣。

**Acceptance Criteria:**
- [ ] 顯示即時功率（W）及當日累計用電（kWh）
- [ ] 提供 7 日、30 日歷史圖表
- [ ] 用電超過閾值時發送通知

---

### US-05 · 安全防護
**As a** 屋主，  
**I want** 在離家時啟動安全模式，並在異常事件（門窗開啟、動作偵測）時立即收到通知，  
**So that** 即使不在家也能掌握住家安全狀態。

**Acceptance Criteria:**
- [ ] 安全模式下所有入侵感測器啟用監控
- [ ] 異常事件 30 秒內推播通知至手機
- [ ] 支援攝影機畫面快照附帶於通知
- [ ] 可設定免打擾白名單（家人到訪不觸發警報）

---

### US-06 · 遠端存取
**As a** 使用者，  
**I want** 在外出時透過手機 App 或瀏覽器遠端控制家中設備，  
**So that** 不論身處何地都能管理家庭環境。

**Acceptance Criteria:**
- [ ] 透過 Nabu Casa 或 WireGuard VPN 提供安全遠端存取
- [ ] Home Assistant Companion App（iOS/Android）完整支援
- [ ] 遠端操作延遲 < 3 秒（一般網路環境）

---

### US-07 · 語音控制
**As a** 使用者，  
**I want** 使用語音指令控制設備，  
**So that** 雙手忙碌時（烹飪、抱小孩）仍能快速操控。

**Acceptance Criteria:**
- [ ] 整合 Google Home 或 Amazon Alexa
- [ ] 支援中文語音指令（透過本地 Whisper 或雲端 STT）
- [ ] 語音意圖辨識後 2 秒內執行動作

---

## Out of Scope (v1)

- 影像串流分析（AI 人臉辨識、物件偵測）
- 多住宅管理
- 自建 Matter/Thread Border Router
- 電費帳單自動申報

---

## Review & Acceptance Checklist

- [ ] 每個 User Story 有明確的 Acceptance Criteria
- [ ] 沒有實作細節洩漏進 spec（無技術選型）
- [ ] 所有邊界條件已識別（Out of Scope 列出）
- [ ] 利害關係人已確認需求優先順序
