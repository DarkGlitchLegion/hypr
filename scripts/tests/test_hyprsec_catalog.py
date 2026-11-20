from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import hyprsec_catalog as catalog


class HyprSecCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "tools.conf"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, text: str) -> list[catalog.Tool]:
        self.path.write_text(text, encoding="utf-8")
        tools = catalog.parse_catalog(self.path)
        catalog.validate_catalog(self.path, tools)
        return tools

    def test_parses_metadata_and_legacy_rows(self) -> None:
        tools = self.write(
            "# comment\n"
            "Forensics|Image checker|file|Identify local file types|Kali Rolling APT|apt|verified|APT dependencies|Kali Linux Rolling|https://www.kali.org/tools/|low|Local files only|Workspace file\n"
            "Development|git|Version control\n"
        )
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0].name, "Image checker")
        self.assertEqual(tools[0].package, "file")
        self.assertEqual(tools[1].package, "git")
        self.assertEqual(tools[1].availability, "verified")

    def test_filters_by_category_and_case_insensitive_search(self) -> None:
        tools = self.write(
            "Forensics|YARA rules|yara|Scan supplied files|Kali Rolling APT|apt|verified|APT|Kali Linux Rolling|https://www.kali.org/tools/|moderate|Local analysis|Workspace\n"
            "Development|Git|git|Version control|Kali Rolling APT|apt|verified|APT|Kali Linux Rolling|https://www.kali.org/tools/|low|Workspace only|Workspace\n"
        )
        results = catalog.filter_tools(tools, category="Forensics", query="SUPPLIED")
        self.assertEqual([tool.package for tool in results], ["yara"])

    def test_scope_only_category_is_not_installable(self) -> None:
        tools = self.write(
            "Wireless Security|Category scope|-|Metadata only|-|none|scope-only|-|Not applicable||n/a|No devices exposed|Lab\n"
        )
        self.assertFalse(tools[0].installable)

    def test_rejects_duplicate_packages(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate package"):
            self.write("Dev|git|Version control\nTools|git|Another description\n")

    def test_merges_default_and_user_catalog_with_user_override(self) -> None:
        default = Path(self.temp.name) / "default.conf"
        default.write_text(
            "Development|git|Version control\n"
            "Wireless Security|Category scope|-|Metadata only|-|none|scope-only|-|Not applicable||n/a|No devices|Lab\n",
            encoding="utf-8",
        )
        self.path.write_text(
            "Development|git|User description\n"
            "Custom|jq|JSON utility\n",
            encoding="utf-8",
        )
        tools = catalog.merge_catalogs([default, self.path])
        self.assertEqual(len(tools), 3)
        git = next(tool for tool in tools if tool.package == "git")
        self.assertEqual(git.description, "User description")
        self.assertIn("Wireless Security", {tool.category for tool in tools})

    def test_rejects_invalid_package_and_non_https_documentation(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid APT package"):
            self.write(
                "Dev|Bad tool|bad package|desc|Kali|apt|verified|APT|Kali|https://www.kali.org/tools/|low|notes|"
            )
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            self.write(
                "Dev|Tool|tool|desc|Kali|apt|verified|APT|Kali|http://example.test/|low|notes|"
            )

    def test_repository_catalog_covers_requested_categories(self) -> None:
        tools = catalog.parse_catalog(ROOT / "hyprsec" / "tools.conf")
        categories = {tool.category for tool in tools}
        self.assertTrue(
            {
                "Information Gathering and OSINT",
                "Vulnerability Assessment",
                "Web Application Security",
                "Wireless Security",
                "Active Directory Assessment",
                "Digital Forensics",
                "Incident Response",
                "Malware Analysis",
                "Reporting and Documentation",
            }.issubset(categories)
        )


if __name__ == "__main__":
    unittest.main()
