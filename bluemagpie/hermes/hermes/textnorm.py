"""文字正規化：阿拉伯數字→中文數字（Piper 中文聲線讀數字不穩）、簡→繁"""
from __future__ import annotations
import re
from opencc import OpenCC
import cn2an

_s2t = OpenCC("s2twp")  # 簡體 → 台灣慣用繁體


def to_traditional(text: str) -> str:
    return _s2t.convert(text)


def _an2cn(s: str) -> str:
    try:
        return cn2an.an2cn(s)
    except Exception:
        return s


def numbers_to_chinese(text: str) -> str:
    # 1) 股票代碼：緊接「現在/怎樣/怎麼樣/股價/漲/跌」的四位數逐字讀 2330 → 二三三零
    text = re.sub(r"(\d{4})(?=\s*(現在|怎樣|怎麼樣|股價|漲|跌|突破|跌破))",
                  lambda m: "".join("零一二三四五六七八九"[int(c)] for c in m.group(1)), text)
    # 2) 百分比：1.2% → 百分之一點二
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", lambda m: "百分之" + _an2cn(m.group(1)), text)
    # 3) 其餘數字
    text = re.sub(r"\d+(?:\.\d+)?", lambda m: _an2cn(m.group(0)), text)
    return text


def for_tts(text: str) -> str:
    t = text.replace("°C", "度").replace("℃", "度")
    t = numbers_to_chinese(to_traditional(t))   # 先轉繁體讓「現在/怎樣」等關鍵字可被偵測
    return to_traditional(t)                      # cn2an 輸出含簡體「点」，再轉一次
