#!/usr/bin/env python3
"""Parse and query the HyprSec pipe-delimited tool catalog."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


PACKAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
FIELDS = (
    "category",
    "name",
    "package",
    "description",
    "source",
    "method",
    "availability",
    "dependencies",
    "compatibility",
    "documentation",
    "risk",
    "notes",
    "prerequisites",
)


@dataclass(frozen=True)
class Tool:
    category: str
    name: str
    package: str
    description: str
    source: str = "Kali Rolling APT"
    method: str = "apt"
    availability: str = "verified"
    dependencies: str = "APT resolves package dependencies"
    compatibility: str = "Kali Linux Rolling"
    documentation: str = ""
    risk: str = "moderate"
    notes: str = ""
    prerequisites: str = ""

    def values(self) -> tuple[str, ...]:
        return tuple(getattr(self, field) for field in FIELDS)

    @property
    def installable(self) -> bool:
        return self.availability in {"verified", "unverified"} and bool(
            PACKAGE_NAME.fullmatch(self.package)
        )


def parse_catalog(path: Path) -> list[Tool]:
    tools: list[Tool] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError(f"Cannot read catalog {path}: {error}") from error

    for line_number, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        columns = [column.strip() for column in line.split("|")]
        if len(columns) == 3:
            category, package, description = columns
            tool = Tool(
                category=category,
                name=package,
                package=package,
                description=description,
                documentation="https://www.kali.org/tools/",
                risk="moderate",
                notes="Legacy catalog entry; availability is checked against the live APT index.",
            )
        elif len(columns) == len(FIELDS):
            tool = Tool(*columns)
        else:
            raise ValueError(
                f"{path}:{line_number}: expected 3 legacy or {len(FIELDS)} metadata fields"
            )
        validate_tool(tool, path, line_number)
        tools.append(tool)
    return tools


def validate_tool(tool: Tool, path: Path, line_number: int) -> None:
    prefix = f"{path}:{line_number}:"
    if not tool.category or not tool.name or not tool.description:
        raise ValueError(f"{prefix} category, name, and description are required")
    if tool.availability == "scope-only":
        if tool.package != "-" or tool.method != "none":
            raise ValueError(f"{prefix} scope-only entries must not have an installable package")
    elif tool.availability not in {"verified", "unverified"}:
        raise ValueError(f"{prefix} unsupported availability value: {tool.availability}")
    elif not PACKAGE_NAME.fullmatch(tool.package):
        raise ValueError(f"{prefix} invalid APT package name: {tool.package}")
    if tool.documentation:
        parsed_url = urlparse(tool.documentation)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError(f"{prefix} documentation URL must use HTTPS")


def validate_catalog(path: Path, tools: list[Tool]) -> None:
    packages: dict[str, int] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        columns = line.split("|")
        package = columns[1] if len(columns) == 3 else columns[2]
        availability = "verified" if len(columns) == 3 else columns[6].strip()
        if availability == "scope-only":
            continue
        if package in packages:
            raise ValueError(
                f"{path}:{line_number}: duplicate package {package!r} "
                f"(first listed on line {packages[package]})"
            )
        packages[package] = line_number


def merge_catalogs(paths: list[Path]) -> list[Tool]:
    merged: list[Tool] = []
    package_positions: dict[str, int] = {}
    categories: set[str] = set()
    for path in paths:
        tools = parse_catalog(path)
        validate_catalog(path, tools)
        for tool in tools:
            if tool.availability == "scope-only":
                if tool.category not in categories:
                    categories.add(tool.category)
                    merged.append(tool)
                continue
            existing_position = package_positions.get(tool.package)
            if existing_position is None:
                package_positions[tool.package] = len(merged)
                merged.append(tool)
            else:
                merged[existing_position] = tool
    return merged


def filter_tools(
    tools: list[Tool], *, category: str = "", query: str = ""
) -> list[Tool]:
    needle = query.casefold()
    return [
        tool
        for tool in tools
        if (not category or tool.category == category)
        and (not needle or needle in " ".join(tool.values()).casefold())
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("categories", "list", "validate"))
    parser.add_argument("catalog", nargs="+", type=Path)
    parser.add_argument("--category", default="")
    parser.add_argument("--query", default="")
    args = parser.parse_args()
    try:
        tools = merge_catalogs(args.catalog)
        if args.command == "validate":
            print(f"Catalog valid: {len(tools)} entries")
        elif args.command == "categories":
            print("\n".join(sorted({tool.category for tool in tools})))
        else:
            for tool in filter_tools(tools, category=args.category, query=args.query):
                print("|".join(tool.values()))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
