# -*- coding: utf-8-sig -*-
"""Phase 3 開源發布前本機安全與隱私盤點掃描器（純 Python 標準庫，無網路呼叫）。

職責：
1. 掃描目標專案目錄下所有自有檔案（含 .env*、設定、文件、原始碼、測試、靜態文字、現有 dist、以及掃描器自身）。
2. 排除第三方依賴與編譯快取目錄（venv / node_modules / __pycache__ 等），並記錄被排除目錄。
3. 絕不靜默略過 PermissionError、OSError、重解析點（symlink / junction）或解碼異常：
   所有跳過項目與原因均記錄於 `skipped_and_coverage_limits`，若非空則 `coverage_complete` 為 False。
4. 對大型與二進位檔案列出相對路徑、大小（bytes）、proposed_scope 與權利/來源狀態（僅標記
   generation_source_available / owner_confirmation_pending 或未知權利不可再散布，不宣稱 safe_to_publish）。
5. 在本機記憶體內偵測：
   - .env* 與一般 JSON / Python / JS / TS / 設定檔中之非佔位機密賦值（case-insensitive）
   - 私鑰標頭、JWT、ghp_ / github_pat_、AWS AKIA/ASIA、Google AIza、sk-、URL user:password@host
   - 秘密環境變數名稱與範本佔位符（如 CLOUDFLARED_TOKEN）
   - Google 發布商 ID / 廣告版位 ID（標記為非秘密之待移除廣告身分資訊）
   - 廣告與追蹤腳本 / 網域（AdSense / GTM / GA / DoubleClick）
   - 個人聯絡 Email
   - 個人 Windows 使用者絕對路徑
   - 舊部署網域（固定遮蔽為 [HOST_REDACTED]，不輸出實際網域字串）
   - 私有區網 IP（RFC1918）或內部主機名稱
6. 尚無 Git 時僅標記 `proposed_scope`（`proposed_candidate_public` vs `proposed_ignored_local_or_generated`），
   後續須與實際 `git check-ignore` 及明確候選清單交叉核對。
7. 將完全去敏結果寫入 `.recovery/phase3/security-findings.json`，並在 stdout 僅印出統計與相對路徑清單。
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_REL_PATH: Final[str] = ".recovery/phase3/security-findings.json"

SKIP_DIR_NAMES: Final[frozenset[str]] = frozenset(
    {
        "venv",
        ".venv",
        "env",
        "node_modules",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
)

# 任意層級皆屬於本機產物/快取的目錄名稱
IGNORED_DIR_NAMES_ANY_LEVEL: Final[frozenset[str]] = frozenset(
    {
        ".claude",
        ".vscode",
        ".playwright-cli",
        "test-results",
        "playwright-report",
        "blob-report",
        ".cache",
        ".recovery",
    }
)

# 任意層級皆屬於本機秘密或憑證的副檔名
CERT_OR_KEY_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".pem",
        ".key",
        ".pfx",
        ".p12",
        ".crt",
        ".der",
    }
)

BINARY_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".tar",
        ".gz",
        ".zip",
        ".7z",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".mp3",
        ".m4a",
        ".wav",
        ".ogg",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".pdf",
        ".pyc",
        ".pyo",
        ".pyd",
        ".dll",
        ".exe",
        ".so",
    }
)

MAX_TEXT_SCAN_BYTES: Final[int] = 30_000_000  # 30 MB 上限，確保 symbol.json (8.8MB) 與 symbol.csv (2MB) 完整進行文字掃描
LARGE_TEXT_DATASET_THRESHOLD_BYTES: Final[int] = 1_000_000  # 1 MB 以上之文字資料集額外記錄於 large_text_datasets_scanned

# 快速前篩正則（涵蓋下方所有通用規則之必要子字串，加速百萬字元級 JSON/CSV 逐行掃描且不漏檢）
RE_LINE_FAST_PREFILTER: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:token|secret|password|passwd|api_key|apikey|private_key|access_key"
    r"|client_secret|credential|auth_token|private key|eyj|gh[pousr]_|github_pat_"
    r"|akia|asia|aiza|sk-|://|pub-|ad_slot|data-ad-"
    r"|google-adsense-account|googlesyndication|doubleclick|googletagmanager"
    r"|google-analytics|adtrafficquality|adsbygoogle|@|users|trycloudflare\.com"
    r"|10\.\d|192\.168\.|172\.(?:1[6-9]|2\d|3[0-1])\.|host\.docker\.internal)"
)

# 1a. .env* 或 shell 風格之機密變數賦值（case-insensitive）
RE_ENV_SECRET_ASSIGN: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:export\s+)?([A-Za-z0-9_]*(?:token|secret|password|passwd|api_key|apikey|private_key|access_key|client_secret|credential|auth_token)[A-Za-z0-9_]*)\s*=\s*(.+?)\s*$",
    re.IGNORECASE,
)

# 1b. 一般 JSON / Python / JS / TS / YAML 之引號字串機密賦值（case-insensitive）
RE_GENERAL_CREDENTIAL_ASSIGN: Final[re.Pattern[str]] = re.compile(
    r"""(?i)(?:^|(?<=[\s,{(\['"]))([a-z0-9_]*(?:token|secret|password|passwd|api_key|apikey|private_key|access_key|client_secret|credential|auth_token)[a-z0-9_]*)["']?\s*[:=]\s*["']([^"'\r\n]{4,})["']"""
)

NON_SECRET_CONFIG_KEYS: Final[frozenset[str]] = frozenset(
    {
        "allow_credentials",
        "with_credentials",
        "withcredentials",
        "tokenizer",
        "css_tokenizer",
        "js_tokens",
    }
)

RE_SEMVER_VALUE: Final[re.Pattern[str]] = re.compile(
    r"^[\^~>=<*v0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$"
)

# 1c. 私鑰標頭
RE_PRIVATE_KEY_HEADER: Final[re.Pattern[str]] = re.compile(
    r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"
)

# 1d. 結構化高風險 Token / API Key（JWT, ghp_*, github_pat_*, AWS AKIA/ASIA, Google AIza, sk-*）
RE_STRUCTURED_TOKEN: Final[re.Pattern[str]] = re.compile(
    r"(?:\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,}\b"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}\b"
    r"|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"
    r"|\bAIza[0-9A-Za-z_-]{35}\b"
    r"|\bsk-[A-Za-z0-9_-]{20,}\b)"
)

# 1e. URL 內嵌 user:password@host 憑證模式（排除 ${VAR} 佔位）
RE_URL_USER_PASSWORD: Final[re.Pattern[str]] = re.compile(
    r"\b[a-zA-Z][a-zA-Z0-9+.-]*://([^/\s:@\"'`]+):([^/\s@\"'`]+)@[^\s/\"'`]+"
)

# 2. 秘密環境變數名稱引用
RE_SECRET_VAR_REF: Final[re.Pattern[str]] = re.compile(
    r"\bCLOUDFLARED_TOKEN\b"
)

# 3. 通用 Google AdSense 發布商 ID / 版位屬性（非秘密金鑰，屬待移除之廣告標記）
RE_AD_PUBLISHER_OR_SLOT: Final[re.Pattern[str]] = re.compile(
    r"(?:\bca-pub-\d{10,20}\b|\bpub-\d{10,20}\b|\bAD_SLOT(?:_LEFT|_RIGHT)?\b|\bdata-ad-slot\b|\bdata-ad-client\b|\bgoogle-adsense-account\b)"
)

# 4. 廣告 / 追蹤腳本與外部網域
RE_AD_TRACKING_URL_OR_SCRIPT: Final[re.Pattern[str]] = re.compile(
    r"(?:googlesyndication\.com|doubleclick\.net|googletagmanager\.com|google-analytics\.com|adtrafficquality\.google|pagead2\.googlesyndication\.com|\badsbygoogle\b)"
)

# 5. 個人聯絡 Email
RE_EMAIL: Final[re.Pattern[str]] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# 6. 個人 Windows 絕對路徑
RE_WINDOWS_USER_PATH: Final[re.Pattern[str]] = re.compile(
    r"[cC]:[\\/][Uu]sers[\\/][^\s\"'`<>|]+"
)

# 7. 公開穿隧服務網域尾綴與可選之自訂私有部署網域（DESTINYORDER_AUDIT_PRIVATE_HOSTS，預設為空）
PRIVATE_HOSTS_ENV_VAR: Final[str] = "DESTINYORDER_AUDIT_PRIVATE_HOSTS"
RE_PUBLIC_TUNNEL_DOMAIN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:https?://)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+trycloudflare\.com\b",
    re.IGNORECASE,
)


def _build_private_hosts_pattern() -> re.Pattern[str] | None:
    """由可選環境變數 DESTINYORDER_AUDIT_PRIVATE_HOSTS（逗號分隔）動態建立私有部署網域正則；預設不含任何私人 hostname。"""
    raw = os.environ.get(PRIVATE_HOSTS_ENV_VAR, "")
    hosts: list[str] = []
    for part in raw.split(","):
        cleaned = part.strip().lower().lstrip(".")
        if cleaned and re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", cleaned):
            hosts.append(re.escape(cleaned))
    if not hosts:
        return None
    joined = "|".join(hosts)
    return re.compile(
        rf"\b(?:https?://)?(?:[a-z0-9-]+\.)*(?:{joined})\b",
        re.IGNORECASE,
    )

# 8. 私有區網 IP（RFC1918）或內部 host
RE_PRIVATE_RFC1918_IP: Final[re.Pattern[str]] = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|host\.docker\.internal)\b"
)

PLACEHOLDER_VALUES: Final[frozenset[str]] = frozenset(
    {
        "",
        "your-token-here",
        "your_token_here",
        "your-cloudflare-tunnel-token",
        "your_cloudflare_tunnel_token",
        "your-cloudflare-tunnel-token-here",
        "changeme",
        "replace-me",
        "replace_me",
        "example",
        "todo",
        "none",
        "null",
        "undefined",
        "false",
        "true",
        "...",
    }
)


def _is_reparse_or_symlink(path: Path) -> bool:
    """檢查是否為 symlink 或 Windows junction / reparse point。"""
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        return True
    file_attrs = getattr(st, "st_file_attributes", 0)
    if file_attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        return True
    return False


def _is_within_root(path: Path, root: Path) -> bool:
    """確保解析後的實體路徑仍在指定 root 之內。"""
    try:
        resolved = path.resolve()
        return resolved == root or root in resolved.parents
    except OSError:
        return False


def _classify_proposed_scope(rel_posix: str) -> str:
    """尚無 Git 時標記 proposed_scope；後續應與實際 git check-ignore 交叉核對。

    注意：playwright.recovery.config.ts 與 e2e/local-recovery.spec.ts 為可公開之核心測試，
    必須歸為 proposed_candidate_public。
    """
    parts = Path(rel_posix).parts
    fname = parts[-1] if parts else rel_posix
    ext = Path(fname).suffix.lower()

    # 1. 任意層級的本機工具產物 / 快取 / IDE / Agent 目錄
    if any(part in IGNORED_DIR_NAMES_ANY_LEVEL for part in parts[:-1]):
        return "proposed_ignored_local_or_generated"

    # 2. 任意層級的 .env / .env.*（僅已清洗之 .env.example 屬於 candidate_public）
    if fname == ".env" or (fname.startswith(".env.") and fname != ".env.example"):
        return "proposed_ignored_local_or_generated"

    # 3. 任意層級的私鑰 / 憑證檔、.log 或 .eslintcache
    if ext in CERT_OR_KEY_EXTENSIONS or ext == ".log" or fname == ".eslintcache":
        return "proposed_ignored_local_or_generated"

    # 4. 專案特定之本機資料、建置產物、備份與待隔離項目
    ignored_prefixes = (
        "memory/",
        "COPY/",
        "backend/data/",
        "frontend/dist/",
    )
    ignored_exact = {
        "CLAUDE.md",
        "destinyorder-images.tar",
        "部署手冊.md",
        "frontend/src/components/BottomAdSlot.vue",
        "frontend/src/components/SideAdSlots.vue",
        "frontend/public/ads.txt",
        "frontend/public/og-image.png",
        "frontend/public/favicon.ico",
        "frontend/public/favicon-48.png",
        "frontend/public/favicon-96.png",
        "frontend/public/favicon-192.png",
        "frontend/public/favicon-512.png",
        "frontend/public/apple-touch-icon.png",
        "frontend/public/audio/One_Life_Left.m4a",
        "frontend/public/audio/One_Life_Left.mp3",
        "scripts/generate_favicon.py",
        "scripts/render_lottery_sfx.py",
    }
    if rel_posix in ignored_exact or rel_posix.startswith(ignored_prefixes):
        return "proposed_ignored_local_or_generated"

    return "proposed_candidate_public"


def _classify_asset_rights(rel_posix: str) -> str:
    """標註二進位與大型資料檔案的來源與權利狀態（不自行宣稱 safe_to_publish）。"""
    if rel_posix in {
        "frontend/public/favicon.ico",
        "frontend/public/favicon-48.png",
        "frontend/public/favicon-96.png",
        "frontend/public/favicon-192.png",
        "frontend/public/favicon-512.png",
        "frontend/public/apple-touch-icon.png",
    }:
        return "generation_source_available (scripts/generate_favicon.py); owner_confirmation_pending"
    if rel_posix.startswith("frontend/dist/") and any(
        rel_posix.endswith(suffix)
        for suffix in (
            "favicon.ico",
            "favicon-48.png",
            "favicon-96.png",
            "favicon-192.png",
            "favicon-512.png",
            "apple-touch-icon.png",
        )
    ):
        return "build_artifact_from_generated_favicon; exclude_dist; owner_confirmation_pending"
    if rel_posix.startswith("COPY/"):
        return "generation_source_available (scripts/render_lottery_sfx.py); local_scratch_copy; owner_confirmation_pending"
    if "One_Life_Left." in rel_posix:
        return "unknown_third_party_audio_rights_unverified; owner_confirmation_pending (do_not_redistribute)"
    if rel_posix.endswith("og-image.png"):
        return "unverified_origin_and_legacy_branding; owner_confirmation_pending (do_not_redistribute)"
    if rel_posix == "destinyorder-images.tar":
        return "local_docker_image_archive_590MB (do_not_publish)"
    if rel_posix.startswith("backend/data/funds/symbol."):
        return "third_party_twse_scraped_dataset_terms_unverified (do_not_redistribute)"
    return "binary_or_large_file_owner_confirmation_pending"


def _is_placeholder_secret_value(raw_val: str) -> bool:
    """判斷設定值是否僅為空白、變數引用或範例佔位符（不在任何輸出中包含 raw_val）。"""
    val = raw_val.strip().rstrip(",;")
    if len(val) >= 2 and val[0] == val[-1] and val[0] in {'"', "'"}:
        val = val[1:-1].strip()
    low = val.lower()
    if low in PLACEHOLDER_VALUES:
        return True
    if RE_SEMVER_VALUE.match(low):
        return True
    if low.startswith(("<", "${", "$", "your-", "your_", "example", "replace", "dummy", "mock", "test_placeholder")):
        return True
    if low.endswith(("_here", "-here", "_placeholder", "-placeholder")):
        return True
    if re.fullmatch(r"[\*\.xX_-]+", low):
        return True
    return False


def _is_benign_config_or_package_key(key_name: str, assigned_val: str) -> bool:
    """排除非機密之布林設定鍵（如 allow_credentials）與套件名稱/版本依賴鍵（如 tokenizer）。"""
    low_key = key_name.strip().lower()
    if low_key in NON_SECRET_CONFIG_KEYS or "tokenizer" in low_key:
        return True
    val_clean = assigned_val.strip().rstrip(",;").strip("\"'")
    if RE_SEMVER_VALUE.match(val_clean):
        return True
    return False


def _read_text_lines(file_path: Path) -> tuple[list[str], str, bool, int]:
    """安全讀取文字檔並回傳 (lines, encoding_name, had_decode_error, literal_ufffd_count)。

    先以 `errors="strict"` 嘗試解碼：
    - 若 strict 解碼成功，代表檔案本身為合法 UTF-16 / UTF-8 文字檔（`had_decode_error = False`）；
      若檔案內容原本已包含字面 `U+FFFD` (`\\ufffd`) 字元，另外統計 `literal_ufffd_count` 供資料品質記錄，
      不視為掃描器解碼失敗。
    - 僅當 strict 解碼拋出 `UnicodeDecodeError` 時，才退回 `errors="replace"` 並標記 `had_decode_error = True`。
    """
    raw = file_path.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        enc_label = "utf-16-le"
        codec = "utf-16-le"
    elif raw.startswith(b"\xfe\xff"):
        enc_label = "utf-16-be"
        codec = "utf-16-be"
    else:
        enc_label = "utf-8"
        codec = "utf-8-sig"

    try:
        text = raw.decode(codec, errors="strict")
        if codec.startswith("utf-16"):
            text = text.lstrip("\ufeff")
        return text.splitlines(), enc_label, False, text.count("\ufffd")
    except UnicodeDecodeError:
        text = raw.decode(codec, errors="replace")
        if codec.startswith("utf-16"):
            text = text.lstrip("\ufeff")
        return text.splitlines(), enc_label, True, 0


def _is_detector_or_test_rule_line(rel_posix: str, line: str) -> bool:
    """判斷是否為掃描器或測試檔中的規則/常數定義行（供附加人工覆核標記，不跳過掃描）。"""
    if rel_posix not in {
        "scripts/audit_publication.py",
        "backend/tests/test_audit_publication.py",
    }:
        return False
    stripped = line.strip()
    return (
        stripped.startswith(("r\"", "r'", "r\"\"\"", "#", "RE_", "\"", "'"))
        or "re.compile" in stripped
    )


def _scan_text_file(
    rel_posix: str,
    proposed_scope: str,
    lines: list[str],
    private_hosts_pattern: re.Pattern[str] | None = None,
) -> list[dict[str, Any]]:
    """逐行掃描單一文字檔（含掃描器自身），回傳完全去敏的 finding 列表。"""
    findings: list[dict[str, Any]] = []
    is_env_file = Path(rel_posix).name.startswith(".env")

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        has_private_host = (
            private_hosts_pattern is not None
            and private_hosts_pattern.search(line) is not None
        )
        if not has_private_host and not RE_LINE_FAST_PREFILTER.search(line):
            continue

        rule_line = _is_detector_or_test_rule_line(rel_posix, line)
        note_suffix = (
            " [detector_or_test_pattern_manual_review_required]"
            if rule_line
            else ""
        )

        # 1. 檢查機密 / Token / 私鑰 / 內嵌帳密
        secret_flagged_on_line = False
        env_match = RE_ENV_SECRET_ASSIGN.match(line)
        if env_match and not stripped.startswith("#"):
            lhs_key = env_match.group(1)
            rhs = env_match.group(2)
            if " #" in rhs and not rhs.startswith(('"', "'")):
                rhs = rhs.split(" #", 1)[0].strip()
            if _is_benign_config_or_package_key(lhs_key, rhs):
                pass
            elif not _is_placeholder_secret_value(rhs):
                findings.append(
                    {
                        "rel_path": rel_posix,
                        "line": idx,
                        "category": "secret_or_token_non_placeholder",
                        "proposed_scope": proposed_scope,
                        "redacted_summary": (
                            "Non-placeholder secret/token assignment detected [VALUE_REDACTED]"
                            + note_suffix
                        ),
                    }
                )
                secret_flagged_on_line = True
            else:
                findings.append(
                    {
                        "rel_path": rel_posix,
                        "line": idx,
                        "category": "secret_env_variable_reference",
                        "proposed_scope": proposed_scope,
                        "redacted_summary": (
                            "Secret environment variable placeholder assignment [PLACEHOLDER_ONLY]"
                            + note_suffix
                        ),
                    }
                )
                secret_flagged_on_line = True

        if not secret_flagged_on_line:
            # 檢查私鑰標頭或結構化高風險 Token（含 .env* / .env.example 中未使用敏感變數名之項目，如 SERVICE_AUTH=github_pat_...）
            if RE_PRIVATE_KEY_HEADER.search(line) or RE_STRUCTURED_TOKEN.search(line):
                findings.append(
                    {
                        "rel_path": rel_posix,
                        "line": idx,
                        "category": "secret_or_token_non_placeholder",
                        "proposed_scope": proposed_scope,
                        "redacted_summary": (
                            "Private key header or structured credential token detected [VALUE_REDACTED]"
                            + note_suffix
                        ),
                    }
                )
                secret_flagged_on_line = True

        if not secret_flagged_on_line:
            # 檢查 URL user:password@host 模式（含 .env* / .env.example 中如 DATABASE_URL=postgres://user:pass@host）
            url_cred_match = RE_URL_USER_PASSWORD.search(line)
            if url_cred_match and not stripped.startswith("#"):
                user_part, pass_part = url_cred_match.group(1), url_cred_match.group(2)
                if not _is_placeholder_secret_value(user_part) and not _is_placeholder_secret_value(pass_part):
                    findings.append(
                        {
                            "rel_path": rel_posix,
                            "line": idx,
                            "category": "secret_or_token_non_placeholder",
                            "proposed_scope": proposed_scope,
                            "redacted_summary": (
                                "URL-embedded user:password credential pattern detected [VALUE_REDACTED]"
                                + note_suffix
                            ),
                        }
                    )
                    secret_flagged_on_line = True

        if not secret_flagged_on_line and not is_env_file:
            # 檢查一般 JSON / Python / JS / TS 機密屬性賦值（case-insensitive）
            for cred_match in RE_GENERAL_CREDENTIAL_ASSIGN.finditer(line):
                cred_key = cred_match.group(1)
                assigned_val = cred_match.group(2)
                if _is_benign_config_or_package_key(cred_key, assigned_val):
                    continue
                if not _is_placeholder_secret_value(assigned_val):
                    findings.append(
                        {
                            "rel_path": rel_posix,
                            "line": idx,
                            "category": "secret_or_token_non_placeholder",
                            "proposed_scope": proposed_scope,
                            "redacted_summary": (
                                "Non-placeholder credential string assignment detected [VALUE_REDACTED]"
                                + note_suffix
                            ),
                        }
                    )
                    secret_flagged_on_line = True
                    break

        if not secret_flagged_on_line and RE_SECRET_VAR_REF.search(line):
            findings.append(
                {
                    "rel_path": rel_posix,
                    "line": idx,
                    "category": "secret_env_variable_reference",
                    "proposed_scope": proposed_scope,
                    "redacted_summary": (
                        "Reference to secret environment variable name [VAR_REDACTED]"
                        + note_suffix
                    ),
                }
            )

        # 2. Google AdSense 發布商 ID / 版位 ID（非秘密金鑰，但屬待移除之個人廣告身分）
        if RE_AD_PUBLISHER_OR_SLOT.search(line):
            findings.append(
                {
                    "rel_path": rel_posix,
                    "line": idx,
                    "category": "ad_tracking_publisher_id",
                    "proposed_scope": proposed_scope,
                    "redacted_summary": (
                        "Advertising publisher/slot identifier (non-secret, slated for removal) [ID_REDACTED]"
                        + note_suffix
                    ),
                }
            )

        # 3. 廣告 / 追蹤腳本與外部網域
        if RE_AD_TRACKING_URL_OR_SCRIPT.search(line):
            findings.append(
                {
                    "rel_path": rel_posix,
                    "line": idx,
                    "category": "ad_tracking_url_or_script",
                    "proposed_scope": proposed_scope,
                    "redacted_summary": (
                        "Advertising/tracking script or domain reference"
                        + note_suffix
                    ),
                }
            )

        # 4. 個人聯絡 Email
        if RE_EMAIL.search(line):
            findings.append(
                {
                    "rel_path": rel_posix,
                    "line": idx,
                    "category": "personal_email",
                    "proposed_scope": proposed_scope,
                    "redacted_summary": (
                        "Personal/contact email address [EMAIL_REDACTED]"
                        + note_suffix
                    ),
                }
            )

        # 5. 個人 Windows 絕對路徑
        if RE_WINDOWS_USER_PATH.search(line):
            findings.append(
                {
                    "rel_path": rel_posix,
                    "line": idx,
                    "category": "personal_windows_path",
                    "proposed_scope": proposed_scope,
                    "redacted_summary": (
                        "Personal Windows user absolute path [PATH_REDACTED]"
                        + note_suffix
                    ),
                }
            )

        # 6. 穿隧服務網域或由 DESTINYORDER_AUDIT_PRIVATE_HOSTS 指定之私有部署網域（摘要只寫 [HOST_REDACTED]）
        if has_private_host or RE_PUBLIC_TUNNEL_DOMAIN.search(line):
            findings.append(
                {
                    "rel_path": rel_posix,
                    "line": idx,
                    "category": "legacy_deployment_domain",
                    "proposed_scope": proposed_scope,
                    "redacted_summary": (
                        "Legacy deployment or tunnel domain reference [HOST_REDACTED]"
                        + note_suffix
                    ),
                }
            )

        # 7. 私有區網 IP 或內部 host
        if RE_PRIVATE_RFC1918_IP.search(line):
            findings.append(
                {
                    "rel_path": rel_posix,
                    "line": idx,
                    "category": "private_ip_or_internal_host",
                    "proposed_scope": proposed_scope,
                    "redacted_summary": (
                        "Private RFC1918 IP or internal host reference [HOST_REDACTED]"
                        + note_suffix
                    ),
                }
            )

    return findings


def _safe_rel_posix(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def run_audit(
    project_root: Path = PROJECT_ROOT,
    output_rel_path: str = DEFAULT_OUTPUT_REL_PATH,
) -> dict[str, Any]:
    all_findings: list[dict[str, Any]] = []
    binary_and_media_assets: list[dict[str, Any]] = []
    large_text_datasets_scanned: list[dict[str, Any]] = []
    literal_ufffd_data_quality_notes: list[dict[str, Any]] = []
    skipped_and_coverage_limits: list[dict[str, str]] = []
    excluded_dependency_or_cache_dirs: list[str] = []
    utf16_files: list[str] = []
    proposed_candidate_public_files: list[str] = []
    proposed_ignored_local_files: list[str] = []
    scanned_text_files_count = 0
    private_hosts_pattern = _build_private_hosts_pattern()

    def _on_walk_error(err: OSError) -> None:
        bad_path = Path(getattr(err, "filename", "") or str(project_root))
        skipped_and_coverage_limits.append(
            {
                "rel_path": _safe_rel_posix(bad_path, project_root),
                "reason": f"os_walk_error:{type(err).__name__}",
            }
        )

    for root, dirs, files in os.walk(
        project_root,
        topdown=True,
        onerror=_on_walk_error,
        followlinks=False,
    ):
        root_path = Path(root)

        kept_dirs: list[str] = []
        for d in sorted(dirs):
            d_path = root_path / d
            rel_d = _safe_rel_posix(d_path, project_root)
            if d in SKIP_DIR_NAMES:
                excluded_dependency_or_cache_dirs.append(rel_d)
                continue
            try:
                is_rep = _is_reparse_or_symlink(d_path)
            except OSError as err:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_d,
                        "reason": f"dir_lstat_error:{type(err).__name__}",
                    }
                )
                continue
            if is_rep:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_d,
                        "reason": "skipped_reparse_point_or_symlink_dir",
                    }
                )
                continue
            if not _is_within_root(d_path, project_root):
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_d,
                        "reason": "skipped_dir_outside_project_root",
                    }
                )
                continue
            kept_dirs.append(d)
        dirs[:] = kept_dirs

        for fname in sorted(files):
            fpath = root_path / fname
            rel_posix = _safe_rel_posix(fpath, project_root)
            if rel_posix == output_rel_path:
                continue

            try:
                is_rep = _is_reparse_or_symlink(fpath)
            except OSError as err:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_posix,
                        "reason": f"file_lstat_error:{type(err).__name__}",
                    }
                )
                continue

            if is_rep:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_posix,
                        "reason": "skipped_reparse_point_or_symlink_file",
                    }
                )
                continue

            if not _is_within_root(fpath, project_root):
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_posix,
                        "reason": "skipped_file_outside_project_root",
                    }
                )
                continue

            try:
                size_bytes = fpath.stat().st_size
            except OSError as err:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_posix,
                        "reason": f"file_stat_error:{type(err).__name__}",
                    }
                )
                continue

            proposed_scope = _classify_proposed_scope(rel_posix)
            if proposed_scope == "proposed_candidate_public":
                proposed_candidate_public_files.append(rel_posix)
            else:
                proposed_ignored_local_files.append(rel_posix)
            ext = fpath.suffix.lower()

            if ext in BINARY_EXTENSIONS:
                binary_and_media_assets.append(
                    {
                        "rel_path": rel_posix,
                        "size_bytes": size_bytes,
                        "proposed_scope": proposed_scope,
                        "rights_and_provenance": _classify_asset_rights(rel_posix),
                    }
                )
                continue

            if size_bytes > MAX_TEXT_SCAN_BYTES:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_posix,
                        "reason": f"text_file_exceeds_max_scan_bytes:{size_bytes}",
                    }
                )
                binary_and_media_assets.append(
                    {
                        "rel_path": rel_posix,
                        "size_bytes": size_bytes,
                        "proposed_scope": proposed_scope,
                        "rights_and_provenance": _classify_asset_rights(rel_posix),
                    }
                )
                continue

            if size_bytes >= LARGE_TEXT_DATASET_THRESHOLD_BYTES:
                large_text_datasets_scanned.append(
                    {
                        "rel_path": rel_posix,
                        "size_bytes": size_bytes,
                        "proposed_scope": proposed_scope,
                        "rights_and_provenance": _classify_asset_rights(rel_posix),
                    }
                )

            try:
                lines, enc, had_decode_error, literal_ufffd_count = _read_text_lines(fpath)
            except OSError as err:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_posix,
                        "reason": f"file_read_error:{type(err).__name__}",
                    }
                )
                continue

            if had_decode_error:
                skipped_and_coverage_limits.append(
                    {
                        "rel_path": rel_posix,
                        "reason": "partial_decode_replacement_characters_encountered",
                    }
                )
            elif literal_ufffd_count > 0:
                literal_ufffd_data_quality_notes.append(
                    {
                        "rel_path": rel_posix,
                        "literal_ufffd_count": literal_ufffd_count,
                        "proposed_scope": proposed_scope,
                        "note": (
                            "Valid strict-decoded text containing pre-existing literal U+FFFD "
                            "characters (data-quality artifact; root cause unverified)"
                        ),
                    }
                )

            if enc.startswith("utf-16"):
                utf16_files.append(rel_posix)

            scanned_text_files_count += 1
            file_findings = _scan_text_file(
                rel_posix,
                proposed_scope,
                lines,
                private_hosts_pattern=private_hosts_pattern,
            )
            all_findings.extend(file_findings)

    # 彙整各類別統計（區分 proposed_candidate_public 與 proposed_ignored_local_or_generated）
    category_summary: dict[str, dict[str, Any]] = {}
    grouped_paths: dict[str, set[str]] = defaultdict(set)
    grouped_public_paths: dict[str, set[str]] = defaultdict(set)
    grouped_ignored_paths: dict[str, set[str]] = defaultdict(set)
    grouped_counts: dict[str, int] = defaultdict(int)
    grouped_public_counts: dict[str, int] = defaultdict(int)
    grouped_ignored_counts: dict[str, int] = defaultdict(int)

    for item in all_findings:
        cat = item["category"]
        rpath = item["rel_path"]
        bucket = item["proposed_scope"]
        grouped_counts[cat] += 1
        grouped_paths[cat].add(rpath)
        if bucket == "proposed_candidate_public":
            grouped_public_counts[cat] += 1
            grouped_public_paths[cat].add(rpath)
        else:
            grouped_ignored_counts[cat] += 1
            grouped_ignored_paths[cat].add(rpath)

    for cat in sorted(grouped_counts.keys()):
        category_summary[cat] = {
            "total_occurrences": grouped_counts[cat],
            "proposed_candidate_public_occurrences": grouped_public_counts[cat],
            "proposed_ignored_local_occurrences": grouped_ignored_counts[cat],
            "proposed_candidate_public_files": sorted(grouped_public_paths[cat]),
            "proposed_ignored_local_files": sorted(grouped_ignored_paths[cat]),
            "all_files": sorted(grouped_paths[cat]),
        }

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_name": "DestinyOrder",
        "scope_note": (
            "All scope classifications are heuristic proposed_scope only and must "
            "be verified against the current `git check-ignore` results "
            "and the explicit staged file manifest."
        ),
        "coverage_complete": len(skipped_and_coverage_limits) == 0,
        "scanned_text_files_count": scanned_text_files_count,
        "proposed_candidate_public_files_count": len(proposed_candidate_public_files),
        "proposed_candidate_public_files": sorted(proposed_candidate_public_files),
        "proposed_ignored_local_files_count": len(proposed_ignored_local_files),
        "utf16_encoded_files": sorted(utf16_files),
        "excluded_dependency_or_cache_dirs": sorted(excluded_dependency_or_cache_dirs),
        "skipped_and_coverage_limits": skipped_and_coverage_limits,
        "total_findings_count": len(all_findings),
        "summary_by_category": category_summary,
        "large_text_datasets_scanned": large_text_datasets_scanned,
        "literal_ufffd_data_quality_notes": literal_ufffd_data_quality_notes,
        "binary_and_media_assets": binary_and_media_assets,
        "findings": all_findings,
    }
    return report


def main(
    project_root: Path = PROJECT_ROOT,
    output_rel_path: str = DEFAULT_OUTPUT_REL_PATH,
) -> int:
    report = run_audit(project_root=project_root, output_rel_path=output_rel_path)
    output_file = project_root / output_rel_path
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=== DestinyOrder Phase 3 Publication Security Audit (Redacted Summary) ===")
    print(f"Output File: {output_rel_path}")
    print(f"Coverage Complete (no skipped/unreadable/reparse files): {report['coverage_complete']}")
    print(f"Scanned Text Files: {report['scanned_text_files_count']}")
    print(
        f"Proposed Candidate Public Files Count: "
        f"{report['proposed_candidate_public_files_count']}"
    )
    print(
        f"Proposed Ignored Local/Generated Files Count: "
        f"{report['proposed_ignored_local_files_count']}"
    )
    print(f"UTF-16 Encoded Files: {', '.join(report['utf16_encoded_files']) or 'None'}")
    print(
        f"Excluded Dependency/Cache Dirs: "
        f"{', '.join(report['excluded_dependency_or_cache_dirs']) or 'None'}"
    )
    print(f"Skipped / Coverage Limit Entries: {len(report['skipped_and_coverage_limits'])}")
    for skip_item in report["skipped_and_coverage_limits"]:
        print(f"  [SKIP/LIMIT] {skip_item['rel_path']} -> {skip_item['reason']}")
    print(f"Binary / Large Assets Inventoried: {len(report['binary_and_media_assets'])}")
    print(f"Total Redacted Findings: {report['total_findings_count']}")
    print("")
    print("--- Findings by Category (Counts & Relative Paths Only) ---")
    for cat, info in report["summary_by_category"].items():
        print(
            f"[{cat}] total={info['total_occurrences']} "
            f"(proposed_candidate_public={info['proposed_candidate_public_occurrences']}, "
            f"proposed_ignored_local={info['proposed_ignored_local_occurrences']})"
        )
        if info["proposed_candidate_public_files"]:
            print(
                f"  proposed_candidate_public_files: "
                f"{', '.join(info['proposed_candidate_public_files'])}"
            )
        if info["proposed_ignored_local_files"]:
            print(
                f"  proposed_ignored_local_files:    "
                f"{', '.join(info['proposed_ignored_local_files'])}"
            )
    print("")
    print("--- Binary & Large Assets Inventory ---")
    for asset in report["binary_and_media_assets"]:
        print(
            f"  {asset['rel_path']} | {asset['size_bytes']} bytes | "
            f"{asset['proposed_scope']} | {asset['rights_and_provenance']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
