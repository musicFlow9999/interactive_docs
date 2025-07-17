import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
from pathlib import Path

BASE_URL = "https://docs.dynatrace.com/"
DOCS_URL = urljoin(BASE_URL, "docs")


def fetch_page(url):
    """Return BeautifulSoup for the given URL."""
    resp = requests.get(url)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')


def extract_links(page_url):
    """Return list of (title, href, description) for sections on a page."""
    soup = fetch_page(page_url)
    items = []
    for a in soup.select('a'):
        href = a.get('href')
        text = a.get_text(strip=True)
        if not href or not text:
            continue
        # Build absolute URL
        link_url = urljoin(BASE_URL, href)
        # Avoid duplicate or external links
        if not link_url.startswith(BASE_URL):
            continue
        desc = ''
        if a.parent and a.parent.find('p'):
            desc = a.parent.find('p').get_text(strip=True)
        items.append({'title': text, 'url': link_url, 'description': desc})
    return items


def crawl_docs(start_url):
    """Crawl docs starting from start_url and build hierarchical structure."""
    visited = set()
    toc = {}
    def _crawl(url, tree):
        if url in visited:
            return
        visited.add(url)
        sections = extract_links(url)
        tree[url] = {
            'title': url.split('/')[-1],
            'sections': [],
        }
        for item in sections:
            if item['url'] in visited:
                continue
            subtree = {}
            tree[url]['sections'].append({
                'title': item['title'],
                'url': item['url'],
                'description': item['description'],
                'subsections': subtree,
            })
            # only crawl pages under /docs
            if item['url'].startswith(DOCS_URL):
                _crawl(item['url'], subtree)
    _crawl(start_url, toc)
    return toc


def render_html(tree, output_file):
    """Render tree to an interactive HTML page."""
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8"/>',
        '<title>Dynatrace Docs Hierarchy</title>',
        '<style>summary {font-weight: bold;} .desc {margin-left:1em; font-style: italic;}</style>',
        '</head>',
        '<body>',
        '<h1>Dynatrace Docs Hierarchy</h1>',
    ]
    def _render_nodes(nodes, indent=0):
        for node_url, data in nodes.items():
            html_parts.append('<details open>')
            html_parts.append(f'<summary><a href="{node_url}" target="_blank">{data["title"]}</a></summary>')
            if data.get('description'):
                html_parts.append(f'<div class="desc">{data["description"]}</div>')
            html_parts.append('<ul>')
            for sec in data.get('sections', []):
                html_parts.append('<li>')
                html_parts.append(
                    f'<a href="{sec["url"]}" target="_blank">{sec["title"]}</a> '
                    f'<a href="#" target="_blank">[internal]</a>'
                )
                if sec['description']:
                    html_parts.append(f'<div class="desc">{sec["description"]}</div>')
                if sec.get('subsections'):
                    html_parts.append('<div>')
                    _render_nodes({sec['url']: sec['subsections']}, indent + 2)
                    html_parts.append('</div>')
                html_parts.append('</li>')
            html_parts.append('</ul>')
            html_parts.append('</details>')
    _render_nodes(tree)
    html_parts.extend(['</body>', '</html>'])
    Path(output_file).write_text('\n'.join(html_parts), encoding='utf-8')


if __name__ == "__main__":
    toc = crawl_docs(DOCS_URL)
    render_html(toc, 'docs_hierarchy.html')
    with open('docs_hierarchy.json', 'w', encoding='utf-8') as f:
        json.dump(toc, f, indent=2)
