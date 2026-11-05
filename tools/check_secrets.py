#!/usr/bin/env python3
"""推送前掃描：git 追蹤中的檔案不得含真實金鑰（憲章 III / 原則 2）。
用法：python3 tools/check_secrets.py [--all]   （--all 掃工作目錄全部檔案，不只 git 追蹤）
結束碼：0 乾淨；1 有疑似金鑰。"""
import re, subprocess, sys, pathlib

PATTERNS = [
    ("xAI / OpenAI key", re.compile(r"\b(?:xai|sk)-[A-Za-z0-9_-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("JWT / HA 長效權杖", re.compile(r"\beyJhbGci[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("AWS key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("私鑰", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("LINE channel secret / token", re.compile(r"(?i)(channel[_ ]?(secret|access[_ ]?token))\s*[:=]\s*['\"]?[A-Za-z0-9+/=]{32,}")),
    ("WireGuard / 長 base64 密鑰", re.compile(r"(?i)(private[_ ]?key|shared[_ ]?secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9+/]{40,}={0,2}['\"]?\s*$", re.M)),
]
PLACEHOLDER = re.compile(r"\.\.\.|<[^>]+>|xxx|changeme|example|your[_-]", re.I)
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".pptx", ".xlsx", ".zip", ".tgz", ".woff", ".woff2", ".ttf"}
SKIP_PATH = ("sop.html", "sop.full.html", "tools/check_secrets.py")


def files():
    if "--all" in sys.argv:
        return [p for p in pathlib.Path(".").rglob("*") if p.is_file() and ".git" not in p.parts]
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout
    return [pathlib.Path(x.decode()) for x in out.split(b"\0") if x]


def main() -> int:
    findings = 0
    for p in files():
        if p.suffix.lower() in SKIP_EXT or any(str(p).endswith(s) for s in SKIP_PATH):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, rx in PATTERNS:
            for m in rx.finditer(text):
                line = text[: m.start()].count("\n") + 1
                snippet = text.splitlines()[line - 1].strip()
                if PLACEHOLDER.search(snippet):
                    continue
                findings += 1
                print(f"{p}:{line}: [{name}] {snippet[:120]}")
    print(f"{'FAIL' if findings else 'OK'}: {findings} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
