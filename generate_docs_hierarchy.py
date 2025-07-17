import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://docs.dynatrace.com/"
DOCS_URL = urljoin(BASE_URL, "docs")


def fetch_page(url: str) -> BeautifulSoup:
    """Return a BeautifulSoup object for the given URL."""
    resp = requests.get(url)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_links(soup: BeautifulSoup) -> list[str]:
    """Return a list of absolute URLs for links under the docs tree."""
    links: list[str] = []
    for a in soup.select("a[href]"):
        href = a["href"]
        full = urljoin(BASE_URL, href)
        if not full.startswith(DOCS_URL):
            continue
        # ignore fragments to avoid duplicates
        parsed = urlparse(full)
        clean = parsed._replace(fragment="").geturl()
        links.append(clean)
    # deduplicate while preserving order
    deduped: list[str] = []
    seen = set()
    for l in links:
        if l not in seen:
            deduped.append(l)
            seen.add(l)
    return deduped


def crawl_page(url: str, visited: set[str]) -> dict | None:
    """Recursively crawl a single page and return a hierarchy node."""
    if url in visited:
        return None
    visited.add(url)

    soup = fetch_page(url)
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

    node = {"title": title, "url": url, "description": desc, "children": []}

    for link in extract_links(soup):
        child = crawl_page(link, visited)
        if child:
            node["children"].append(child)
    return node


def crawl_docs(start_url: str) -> dict:
    """Return the full hierarchy starting from ``start_url``."""
    visited: set[str] = set()
    root = crawl_page(start_url, visited)
    return root if root else {}


def render_html(root: dict, output_file: str) -> None:
    """Render a hierarchy node to an interactive HTML file."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'/>",
        "<title>Dynatrace Docs Hierarchy</title>",
        "<style>.desc{margin-left:1em;font-style:italic;}</style>",
        "</head>",
        "<body>",
        "<h1>Dynatrace Docs Hierarchy</h1>",
        "<ul>",
    ]
    def _render(node: dict) -> None:
        html_parts.append("<li>")
        html_parts.append(
            f'<a href="{node["url"]}" target="_blank">{node["title"]}</a> '
            f'<a href="#" target="_blank">[internal]</a>'
        )
        if node.get("description"):
            html_parts.append(f'<div class="desc">{node["description"]}</div>')
        if node.get("children"):
            html_parts.append("<ul>")
            for child in node["children"]:
                _render(child)
            html_parts.append("</ul>")
        html_parts.append("</li>")

    _render(root)
    html_parts.extend(["</ul>", "</body>", "</html>"])
    Path(output_file).write_text("\n".join(html_parts), encoding="utf-8")


if __name__ == "__main__":
    toc = crawl_docs(DOCS_URL)
    render_html(toc, 'docs_hierarchy.html')
    with open('docs_hierarchy.json', 'w', encoding='utf-8') as f:
        json.dump(toc, f, indent=2)
