#!/usr/bin/env python3
"""Scrape ordinance text from Municode's internal API.

Usage:
    python scripts/scrape_municode.py                         # scrape all target chapters
    python scripts/scrape_municode.py --chapters 14.1 35      # scrape specific chapters
    python scripts/scrape_municode.py --list                  # list available chapters
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Municode API configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://library.municode.com/api"
STATE = "va"
CLIENT_NAME = "roanoke"

# Target chapters most relevant to MuniciPal
TARGET_CHAPTERS = {
    "2": "Administration",
    "7": "Building Regulations",
    "14.1": "Solid Waste Management",
    "19": "License Tax Code",
    "20": "Motor Vehicles and Traffic",
    "26": "Sewers and Sewage Disposal",
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "ordinances" / "roanoke"


# ---------------------------------------------------------------------------
# HTML → plain text converter
# ---------------------------------------------------------------------------

class HTMLToText(HTMLParser):
    """Minimal HTML→text converter that preserves structure."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip = True
        elif tag in ("p", "div", "br", "li", "tr"):
            self._parts.append("\n")
        elif tag in ("h1", "h2", "h3", "h4", "h5"):
            self._parts.append("\n## ")
        elif tag == "td":
            self._parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False
        elif tag in ("h1", "h2", "h3", "h4", "h5"):
            self._parts.append("\n")
        elif tag in ("p", "div", "li", "tr", "table"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse multiple blank lines
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        # Collapse spaces
        raw = re.sub(r"[ \t]+", " ", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    """Convert HTML to clean plain text."""
    parser = HTMLToText()
    parser.feed(html)
    return parser.get_text()


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

@dataclass
class MunicodeClient:
    """Client for Municode's internal API."""

    base_url: str = BASE_URL
    state: str = STATE
    client_name: str = CLIENT_NAME
    session: requests.Session = field(default_factory=requests.Session)
    client_id: int | None = None
    product_id: int | None = None
    job_id: int | None = None

    def __post_init__(self) -> None:
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "x-csrf": "1",
            "Referer": f"https://library.municode.com/{self.state}/{self.client_name}/codes/code_of_ordinances",
        })
        self.session.cookies.set("visitedClients", "[4095]")

    def discover(self) -> None:
        """Discover client/product/job IDs for the configured municipality."""
        # Get client ID
        r = self.session.get(
            f"{self.base_url}/Clients/name",
            params={"clientName": self.client_name, "stateAbbr": self.state},
        )
        r.raise_for_status()
        data = r.json()
        self.client_id = data.get("ClientID") or data.get("ClientId")
        print(f"  Client ID: {self.client_id}")

        # Get product ID (code of ordinances)
        r = self.session.get(
            f"{self.base_url}/Products/name",
            params={"clientId": self.client_id, "productName": "code of ordinances"},
        )
        r.raise_for_status()
        data = r.json()
        self.product_id = data.get("ProductId") or data.get("ProductID")
        print(f"  Product ID: {self.product_id}")

        # Get latest job ID (version)
        r = self.session.get(f"{self.base_url}/Jobs/latest/{self.product_id}")
        r.raise_for_status()
        data = r.json()
        self.job_id = data.get("Id") or data.get("JobId")
        print(f"  Job ID (version): {self.job_id}")

    def get_toc(self) -> dict:
        """Get the table of contents (root node with Children)."""
        r = self.session.get(
            f"{self.base_url}/codesToc",
            params={"jobId": self.job_id, "productId": self.product_id},
        )
        r.raise_for_status()
        return r.json()

    def get_children(self, node_id: str) -> list[dict]:
        """Get child nodes of a TOC node."""
        r = self.session.get(
            f"{self.base_url}/codesToc/children",
            params={
                "jobId": self.job_id,
                "nodeId": node_id,
                "productId": self.product_id,
            },
        )
        r.raise_for_status()
        return r.json()

    def get_content(self, node_id: str) -> str:
        """Get the HTML content for a node."""
        r = self.session.get(
            f"{self.base_url}/CodesContent",
            params={
                "jobId": self.job_id,
                "nodeId": node_id,
                "productId": self.product_id,
            },
        )
        r.raise_for_status()
        data = r.json()
        # Content is in Docs[].Content
        docs = data.get("Docs", [])
        if docs:
            return docs[0].get("Content", "")
        return ""


# ---------------------------------------------------------------------------
# Scraper logic
# ---------------------------------------------------------------------------

def find_chapter_node(children: list[dict], chapter_num: str) -> dict | None:
    """Find a chapter node matching the given number in the Children list."""
    target_lower = f"chapter {chapter_num}".lower()
    for node in children:
        if not isinstance(node, dict):
            continue
        heading = node.get("Heading", "").lower().strip()
        # Match "Chapter X -" or "Chapter X.Y -"
        if heading.startswith(target_lower + " ") or heading.startswith(target_lower + " -"):
            return node
    # Also search inside nested code nodes (e.g. CORO197901)
    for node in children:
        if not isinstance(node, dict):
            continue
        if node.get("HasChildren"):
            sub_children = node.get("Children", [])
            if sub_children:
                found = find_chapter_node(sub_children, chapter_num)
                if found:
                    return found
    return None


def collect_leaf_nodes(client: MunicodeClient, node_id: str, depth: int = 0) -> list[dict]:
    """Recursively collect all leaf (content) nodes under a parent."""
    children = client.get_children(node_id)
    time.sleep(0.3)  # Rate limit

    leaves: list[dict] = []
    for child in children:
        if child.get("HasChildren"):
            leaves.extend(collect_leaf_nodes(client, child["Id"], depth + 1))
        else:
            leaves.append(child)
    return leaves


def scrape_chapter(
    client: MunicodeClient,
    chapter_num: str,
    chapter_title: str,
    toc: list[dict],
) -> str | None:
    """Scrape a full chapter and return markdown content."""
    # Find the chapter in the TOC
    node = find_chapter_node(toc, chapter_num)
    if not node:
        print(f"  ⚠  Chapter {chapter_num} not found in TOC")
        return None

    print(f"  📖 Chapter {chapter_num} - {chapter_title}")
    print(f"     Node ID: {node['Id']}")

    # Get the full chapter content directly (Municode returns all sections)
    html = client.get_content(node["Id"])
    time.sleep(0.5)  # Rate limit

    if not html:
        print("     ⚠  No content returned, trying leaf nodes...")
        # Fall back: collect leaf nodes and get each one
        leaves = collect_leaf_nodes(client, node["Id"])
        parts = []
        for leaf in leaves:
            leaf_html = client.get_content(leaf["Id"])
            if leaf_html:
                parts.append(leaf_html)
            time.sleep(0.3)
        html = "\n".join(parts)

    if not html:
        print("     ⚠  No content found")
        return None

    # Convert HTML to markdown-style text
    text = html_to_text(html)

    # Add header
    md = f"# Chapter {chapter_num} - {chapter_title.upper()}\n\n"
    md += f"*Source: City of Roanoke Code of Ordinances, via Municode*\n"
    md += f"*URL: https://library.municode.com/va/roanoke/codes/code_of_ordinances?nodeId={node['Id']}*\n\n"
    md += "---\n\n"
    md += text

    print(f"     ✅ {len(text):,} characters extracted")
    return md


def list_chapters(client: MunicodeClient, toc: list[dict]) -> None:
    """List all available chapters."""
    print("\nAvailable chapters:\n")

    def print_nodes(nodes: list[dict], indent: int = 0) -> None:
        for n in nodes:
            prefix = "  " * indent
            marker = "📁" if n.get("HasChildren") else "📄"
            print(f"{prefix}{marker} {n.get('Heading', '?')}  [{n.get('Id', '?')}]")
            if n.get("HasChildren") and indent < 1:
                try:
                    children = client.get_children(n["Id"])
                    time.sleep(0.2)
                    print_nodes(children, indent + 1)
                except Exception:
                    pass

    print_nodes(toc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Roanoke ordinances from Municode")
    parser.add_argument("--chapters", nargs="*", help="Specific chapter numbers to scrape")
    parser.add_argument("--list", action="store_true", help="List available chapters")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    print(f"🏛️  Municode Scraper — {CLIENT_NAME.title()}, {STATE.upper()}")
    print("=" * 50)

    client = MunicodeClient()

    print("\n📡 Discovering API parameters...")
    client.discover()

    print("\n📋 Loading table of contents...")
    toc_root = client.get_toc()

    # TOC is a root dict with Children
    toc = toc_root.get("Children", []) if isinstance(toc_root, dict) else toc_root

    if args.list:
        list_chapters(client, toc)
        return

    # Determine which chapters to scrape
    chapters = TARGET_CHAPTERS
    if args.chapters:
        chapters = {k: v for k, v in TARGET_CHAPTERS.items() if k in args.chapters}
        if not chapters:
            # Try matching by partial number
            chapters = {
                k: v for k, v in TARGET_CHAPTERS.items()
                if any(k.startswith(c) for c in args.chapters)
            }

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔍 Scraping {len(chapters)} chapters...")
    scraped = 0
    for ch_num, ch_title in chapters.items():
        content = scrape_chapter(client, ch_num, ch_title, toc)
        if content:
            filename = f"ch_{ch_num.replace('.', '_')}_{ch_title.lower().replace(' ', '_')}.md"
            filepath = out_dir / filename
            filepath.write_text(content, encoding="utf-8")
            print(f"     💾 Saved to {filepath.relative_to(Path.cwd())}")
            scraped += 1
        time.sleep(1)  # Be respectful

    print(f"\n✅ Done! Scraped {scraped}/{len(chapters)} chapters to {out_dir}")
    print(f"\nNext steps:")
    print(f"  python scripts/seed_knowledge.py --source {out_dir}")


if __name__ == "__main__":
    main()
