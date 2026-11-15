"""リポジトリ全体の秘密情報スキャン。

公開リポジトリ化に備え、実物の認証情報らしいパターンが
ソースコードやデータファイルに混入していないことを確認する。
tests/ ディレクトリ自体（このファイルを含む）はスキャン対象から除外する。
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# スキャン対象から除外するディレクトリ
EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", "tests"}
# バイナリとして扱いスキャンしない拡張子
SKIPPED_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".woff", ".woff2"}

# 実物の認証情報らしいパターン
SECRET_PATTERNS = [
    ("Google APIキー", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("GitHub PAT (classic)", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub PAT (fine-grained)", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("APIキー一般 (sk-...)", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("秘密鍵", re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY")),
]

# 変数への直書き代入パターン（プレースホルダは許容リストで除外）
ASSIGNMENT_PATTERN = re.compile(
    r"(api_key|app_password|secret|token)\s*=\s*[\"']([^\"'\s]{12,})[\"']",
    re.IGNORECASE,
)
PLACEHOLDER_MARKERS = ("your-", "your_", "example", "xxx", "os.getenv", "...", "placeholder", "dummy")


def _iter_target_files():
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        if path.suffix.lower() in SKIPPED_SUFFIXES:
            continue
        yield path


def test_no_secrets_in_repo():
    findings = []
    for path in _iter_target_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(REPO_ROOT)
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                findings.append(f"{rel}: {label} らしい文字列 ({match.group(0)[:8]}...)")
        for match in ASSIGNMENT_PATTERN.finditer(text):
            value = match.group(2)
            if any(marker in value.lower() for marker in PLACEHOLDER_MARKERS):
                continue
            findings.append(f"{rel}: 認証情報の直書き代入らしい行 ({match.group(1)} = ...)")
    assert not findings, "秘密情報らしいパターンを検出しました:\n" + "\n".join(findings)
