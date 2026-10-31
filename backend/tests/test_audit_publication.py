# -*- coding: utf-8-sig -*-
"""自測：以有限合成樣本驗證 scripts/audit_publication.py 的規則檢出與遮蔽輸出行為（純標準庫）。

執行方式（於專案根目錄）：
    .\\venv\\Scripts\\python.exe -B -m unittest discover -s backend/tests -v
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts import audit_publication  # noqa: E402


class AuditPublicationSelfTest(unittest.TestCase):
    """驗證合成假 secret 不會出現在 report/stdout，且 example 佔位符不誤判為真 secret。"""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_synthetic_secrets_detected_and_never_leaked_to_report_or_stdout(self) -> None:
        # 動態組裝合成秘密值與鍵名，避免測試原始碼本身在靜態掃描時產生假陽性
        synth_env_secret = "cf_live_" + ("9A8b7C6d" * 4)
        synth_gh_pat = "github_pat_" + ("11AAbbCCdd" * 3)
        synth_aws_key = "AKIA" + ("ABCD1234" * 2)
        synth_json_secret = "SuperJson_" + ("XyZ987" * 2)
        synth_url_pwd = "UrlPass_" + ("QwErTy12" * 2)
        synth_email = "private.owner" + "@" + "example-personal.org"
        synth_domain = "legacy.example.invalid"
        cf_var_name = "CLOUDFLARED_" + "TOKEN"
        api_key_name = "API_" + "KEY"
        client_secret_key = "Client_" + "Secret"
        auth_token_key = "auth_" + "token"

        # 1. 本機 .env（應歸入 proposed_ignored_local_or_generated 且檢出真 secret）
        (self.root / ".env").write_text(
            f"{cf_var_name}={synth_env_secret}\n",
            encoding="utf-8",
        )

        # 2. .env.example（僅含佔位符，不得檢出 secret_or_token_non_placeholder）
        (self.root / ".env.example").write_text(
            f"{cf_var_name}=your-cloudflare-tunnel-token-here\n"
            f"{api_key_name}=<replace-me>\n",
            encoding="utf-8",
        )

        # 3. 候選公開設定與程式碼檔（含 JSON 大小寫混用 credential、github_pat_、AWS key、URL user:pass、舊網域、Email）
        src_dir = self.root / "frontend" / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "sample_config.ts").write_text(
            f'const cfg = {{"{client_secret_key}": "{synth_json_secret}"}};\n'
            f'const pat = "{synth_gh_pat}";\n'
            f'const aws = "{synth_aws_key}";\n'
            f'const dbUrl = "postgresql://dbadmin:{synth_url_pwd}@192.168.1.50:5432/prod";\n'
            f'const contact = "{synth_email}";\n'
            f'const site = "https://{synth_domain}/";\n',
            encoding="utf-8",
        )

        # 4. 驗證核心測試檔屬於 proposed_candidate_public，而 .playwright-cli / test-results 屬於 ignored
        e2e_dir = self.root / "frontend" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        (self.root / "frontend" / "playwright.recovery.config.ts").write_text(
            f'export default {{ baseURL: "https://{synth_domain}" }}\n',
            encoding="utf-8",
        )
        (e2e_dir / "local-recovery.spec.ts").write_text(
            f'// contact: {synth_email}\n',
            encoding="utf-8",
        )

        pw_cli_dir = self.root / "frontend" / ".playwright-cli"
        pw_cli_dir.mkdir(parents=True, exist_ok=True)
        (pw_cli_dir / "state.json").write_text(
            f'{{"{auth_token_key}": "{synth_env_secret}"}}\n',
            encoding="utf-8",
        )

        # 5. 二進位 favicon 權利標記驗證（不得標為 safe_to_publish）
        pub_dir = self.root / "frontend" / "public"
        pub_dir.mkdir(parents=True, exist_ok=True)
        (pub_dir / "favicon-48.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        buf = io.StringIO()
        with (
            unittest.mock.patch.dict(
                os.environ,
                {"DESTINYORDER_AUDIT_PRIVATE_HOSTS": synth_domain},
                clear=False,
            ),
            contextlib.redirect_stdout(buf),
        ):
            exit_code = audit_publication.main(
                project_root=self.root,
                output_rel_path=".recovery/phase3/security-findings.json",
            )
        stdout_text = buf.getvalue()
        self.assertEqual(exit_code, 0)

        report_file = self.root / ".recovery" / "phase3" / "security-findings.json"
        self.assertTrue(report_file.is_file())
        report_raw = report_file.read_text(encoding="utf-8")
        report = json.loads(report_raw)

        # A. 確保任何合成秘密、私密信箱、舊網域字串皆未出現在 JSON 報告或 stdout
        for sensitive in (
            synth_env_secret,
            synth_gh_pat,
            synth_aws_key,
            synth_json_secret,
            synth_url_pwd,
            synth_email,
            synth_domain,
        ):
            self.assertNotIn(sensitive, report_raw)
            self.assertNotIn(sensitive, stdout_text)

        # B. 驗證 .env.example 的佔位符不會被當成非佔位真 secret
        findings = report["findings"]
        example_secret_hits = [
            f
            for f in findings
            if f["rel_path"] == ".env.example"
            and f["category"] == "secret_or_token_non_placeholder"
        ]
        self.assertEqual(example_secret_hits, [])

        example_ref_hits = [
            f
            for f in findings
            if f["rel_path"] == ".env.example"
            and f["category"] == "secret_env_variable_reference"
        ]
        self.assertEqual(len(example_ref_hits), 2)

        # C. 驗證 .env 與 sample_config.ts 的非佔位機密全數檢出
        real_secret_hits = [
            f
            for f in findings
            if f["rel_path"] == "frontend/src/sample_config.ts"
            and f["category"] == "secret_or_token_non_placeholder"
        ]
        self.assertEqual(len(real_secret_hits), 4)

        # D. 驗證 playwright.recovery.config.ts 與 local-recovery.spec.ts 為 proposed_candidate_public
        scope_by_path = {f["rel_path"]: f["proposed_scope"] for f in findings}
        self.assertEqual(
            scope_by_path.get("frontend/playwright.recovery.config.ts"),
            "proposed_candidate_public",
        )
        self.assertEqual(
            scope_by_path.get("frontend/e2e/local-recovery.spec.ts"),
            "proposed_candidate_public",
        )
        self.assertEqual(
            scope_by_path.get("frontend/.playwright-cli/state.json"),
            "proposed_ignored_local_or_generated",
        )
        self.assertEqual(
            scope_by_path.get(".env"),
            "proposed_ignored_local_or_generated",
        )

        # E. 驗證 favicon 權利標記為 owner_confirmation_pending 而非 safe_to_publish
        assets = {a["rel_path"]: a for a in report["binary_and_media_assets"]}
        self.assertIn("frontend/public/favicon-48.png", assets)
        rights = assets["frontend/public/favicon-48.png"]["rights_and_provenance"]
        self.assertIn("generation_source_available", rights)
        self.assertIn("owner_confirmation_pending", rights)
        self.assertNotIn("safe_to_publish", rights)

    def test_decode_replacement_is_recorded_in_coverage_limits(self) -> None:
        # 寫入含無效 UTF-8 byte 的文字檔，驗證不會靜默略過且 coverage_complete 為 False
        bad_file = self.root / "broken_encoding.txt"
        bad_file.write_bytes(b"normal line\n\xff\xfeinvalid utf8 middle \x80\x81\n")

        report = audit_publication.run_audit(project_root=self.root)
        self.assertFalse(report["coverage_complete"])
        reasons = {
            item["rel_path"]: item["reason"]
            for item in report["skipped_and_coverage_limits"]
        }
        self.assertEqual(
            reasons.get("broken_encoding.txt"),
            "partial_decode_replacement_characters_encountered",
        )

    def test_false_positive_cors_and_lockfile_package_tokens_are_ignored_while_real_tokens_trigger(
        self,
    ) -> None:
        """驗證 allow_credentials=False 與 package-lock.json 套件名稱含 token 不誤判為機密。"""
        (self.root / "backend").mkdir(parents=True, exist_ok=True)
        (self.root / "backend" / "main.py").write_text(
            "app.add_middleware(\n"
            "    CORSMiddleware,\n"
            "    allow_credentials=False,\n"
            ")\n",
            encoding="utf-8",
        )

        (self.root / "frontend").mkdir(parents=True, exist_ok=True)
        (self.root / "frontend" / "package-lock.json").write_text(
            '{\n'
            '  "packages": {\n'
            '    "node_modules/@csstools/css-tokenizer": {\n'
            '      "version": "2.2.0"\n'
            '    },\n'
            '    "node_modules/js-tokens": {\n'
            '      "version": "4.0.0"\n'
            '    }\n'
            '  },\n'
            '  "dependencies": {\n'
            '    "@csstools/css-tokenizer": "^2.2.0",\n'
            '    "js-tokens": "^4.0.0"\n'
            '  }\n'
            '}\n',
            encoding="utf-8",
        )

        report = audit_publication.run_audit(project_root=self.root)
        secret_hits = [
            f
            for f in report["findings"]
            if f["category"]
            in {
                "secret_or_token_non_placeholder",
                "secret_env_variable_reference",
            }
        ]
        self.assertEqual(secret_hits, [])

    def test_oversized_text_file_is_recorded_in_coverage_limits_and_sets_coverage_incomplete(
        self,
    ) -> None:
        """若文字檔超過 MAX_TEXT_SCAN_BYTES 未掃描，必須記錄於 skipped_and_coverage_limits 且 coverage_complete 為 False。"""
        big_json = self.root / "huge.json"
        big_json.write_text('{"hello": "' + ("a" * 200) + '"}\n', encoding="utf-8")

        with unittest.mock.patch.object(audit_publication, "MAX_TEXT_SCAN_BYTES", 64):
            report = audit_publication.run_audit(project_root=self.root)

        self.assertFalse(report["coverage_complete"])
        reasons = {
            item["rel_path"]: item["reason"]
            for item in report["skipped_and_coverage_limits"]
        }
        self.assertIn("huge.json", reasons)
        self.assertTrue(
            reasons["huge.json"].startswith("text_file_exceeds_max_scan_bytes:")
        )

    def test_valid_utf8_with_literal_ufffd_is_not_marked_as_decode_failure(
        self,
    ) -> None:
        """合法 UTF-8 內含原已存在之字面 U+FFFD 時，coverage_complete 應為 True 並記錄於 literal_ufffd_data_quality_notes。"""
        data_file = self.root / "symbol_sample.json"
        data_file.write_text(
            '{"name": "示例\ufffd公司", "note": "含字面\ufffd字元"}\n',
            encoding="utf-8-sig",
        )

        report = audit_publication.run_audit(project_root=self.root)
        self.assertTrue(report["coverage_complete"])
        self.assertEqual(report["skipped_and_coverage_limits"], [])

        notes = {
            item["rel_path"]: item["literal_ufffd_count"]
            for item in report["literal_ufffd_data_quality_notes"]
        }
        self.assertEqual(notes.get("symbol_sample.json"), 2)

    def test_env_files_detect_url_credentials_and_structured_tokens_under_non_secret_key_names(
        self,
    ) -> None:
        """驗證 .env.example 與 .env.local 內非敏感鍵名（如 DATABASE_URL / SERVICE_AUTH）之內嵌帳密與結構化 PAT 皆能檢出且不外洩。"""
        synth_pat = "github_pat_" + ("99ZZyyXXww" * 3)
        synth_db_pass = "DbLivePass_" + ("77665544" * 2)

        (self.root / ".env.local").write_text(
            f"DATABASE_URL=postgresql://app_user:{synth_db_pass}@db.internal:5432/destiny\n"
            f"SERVICE_AUTH={synth_pat}\n",
            encoding="utf-8",
        )
        (self.root / ".env.example").write_text(
            "DATABASE_URL=postgresql://your_user:your_password@127.0.0.1:5432/destiny\n"
            f"LEAKED_EXAMPLE_URL=postgresql://admin:{synth_db_pass}@127.0.0.1:5432/destiny\n"
            f"LEAKED_EXAMPLE_PAT={synth_pat}\n",
            encoding="utf-8",
        )

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = audit_publication.main(
                project_root=self.root,
                output_rel_path=".recovery/phase3/security-findings.json",
            )
        stdout_text = buf.getvalue()
        self.assertEqual(exit_code, 0)

        report_file = self.root / ".recovery" / "phase3" / "security-findings.json"
        report_raw = report_file.read_text(encoding="utf-8")
        report = json.loads(report_raw)

        for sensitive in (synth_pat, synth_db_pass):
            self.assertNotIn(sensitive, report_raw)
            self.assertNotIn(sensitive, stdout_text)

        env_local_hits = [
            f
            for f in report["findings"]
            if f["rel_path"] == ".env.local"
            and f["category"] == "secret_or_token_non_placeholder"
        ]
        self.assertEqual(len(env_local_hits), 2)

        env_example_hits = [
            f
            for f in report["findings"]
            if f["rel_path"] == ".env.example"
            and f["category"] == "secret_or_token_non_placeholder"
        ]
        self.assertEqual(len(env_example_hits), 2)
        self.assertEqual([f["line"] for f in env_example_hits], [2, 3])

    def test_private_hosts_env_detects_configured_host_without_leaking_and_defaults_to_none(
        self,
    ) -> None:
        """驗證未設定 DESTINYORDER_AUDIT_PRIVATE_HOSTS 時預設不含任何私人 hostname，設定後可偵測且絕不外洩至報告或 stdout。"""
        fictitious_host_1 = "legacy.example.invalid"
        fictitious_host_2 = "stage-internal.example.invalid"
        tunnel_host = "preview-box.trycloudflare.com"

        sample_file = self.root / "config_hosts.txt"
        sample_file.write_text(
            f"origin_a = https://app.{fictitious_host_1}/path\n"
            f"origin_b = {fictitious_host_2}\n"
            f"tunnel_url = https://{tunnel_host}/api\n",
            encoding="utf-8",
        )

        # 1. 未設定 DESTINYORDER_AUDIT_PRIVATE_HOSTS（空字串）時，僅通用 trycloudflare.com 觸發，不憑空帶入任何私人網域
        with unittest.mock.patch.dict(
            os.environ,
            {"DESTINYORDER_AUDIT_PRIVATE_HOSTS": ""},
            clear=False,
        ):
            default_report = audit_publication.run_audit(project_root=self.root)

        default_domain_hits = [
            f
            for f in default_report["findings"]
            if f["rel_path"] == "config_hosts.txt"
            and f["category"] == "legacy_deployment_domain"
        ]
        self.assertEqual([f["line"] for f in default_domain_hits], [3])

        # 2. 以 mock.patch.dict 指定虛構私有 host 清單時，3 行皆能檢出且報告/stdout 完全不外洩原值
        buf = io.StringIO()
        with (
            unittest.mock.patch.dict(
                os.environ,
                {
                    "DESTINYORDER_AUDIT_PRIVATE_HOSTS": (
                        f"{fictitious_host_1}, {fictitious_host_2}"
                    )
                },
                clear=False,
            ),
            contextlib.redirect_stdout(buf),
        ):
            exit_code = audit_publication.main(
                project_root=self.root,
                output_rel_path=".recovery/phase3/security-findings.json",
            )
        stdout_text = buf.getvalue()
        self.assertEqual(exit_code, 0)

        report_file = self.root / ".recovery" / "phase3" / "security-findings.json"
        report_raw = report_file.read_text(encoding="utf-8")
        configured_report = json.loads(report_raw)

        for host_val in (fictitious_host_1, fictitious_host_2, tunnel_host):
            self.assertNotIn(host_val, report_raw)
            self.assertNotIn(host_val, stdout_text)

        configured_hits = [
            f
            for f in configured_report["findings"]
            if f["rel_path"] == "config_hosts.txt"
            and f["category"] == "legacy_deployment_domain"
        ]
        self.assertEqual([f["line"] for f in configured_hits], [1, 2, 3])
        for hit in configured_hits:
            self.assertIn("[HOST_REDACTED]", hit["redacted_summary"])


if __name__ == "__main__":
    unittest.main()
