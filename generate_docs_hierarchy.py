#!/usr/bin/env python3
"""Generate interactive HTML from a Dynatrace taxonomy JSON file."""
import json
import argparse
from pathlib import Path


def build_html(data: dict) -> str:
    json_str = json.dumps(data)
    html = f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Dynatrace Docs Hierarchy</title>
<style>
 body {{ font-family: Arial, sans-serif; }}
 ul {{ list-style: none; padding-left: 1em; }}
 li {{ margin: 4px 0; }}
 summary {{ cursor: pointer; font-weight: bold; }}
 button {{ margin-left: 4px; }}
 .description {{ color: #555; margin-left: 4px; }}
</style>
</head>
<body>
<h1>Dynatrace Documentation Hierarchy</h1>
<div id="tree"></div>
<script id="taxonomy-data" type="application/json">{json_str}</script>
<script>
const data = JSON.parse(document.getElementById('taxonomy-data').textContent);
function createSection(section) {{
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = section.title;
  details.appendChild(summary);
  const ul = document.createElement('ul');
  if (section.pages) {{
    section.pages.forEach(pg => {{
      const li = document.createElement('li');
      li.innerHTML = `<a href="${{pg.url}}" target="_blank">${{pg.title}}</a>` +
                     `<span class="description"> - ${{pg.description}}</span>` +
                     ` <span class="internal-link" data-url="${{pg.url}}"></span>`;
      ul.appendChild(li);
    }});
  }}
  if (section.subsections) {{
    Object.values(section.subsections).forEach(sub => {{
      ul.appendChild(createSection(sub));
    }});
  }}
  details.appendChild(ul);
  return details;
}}
const container = document.getElementById('tree');
Object.values(data.structure).forEach(sec => container.appendChild(createSection(sec)));
function refreshLinks() {{
  document.querySelectorAll('.internal-link').forEach(span => {{
    const url = span.dataset.url;
    const stored = localStorage.getItem('internal-' + url);
    if (stored) {{
      span.innerHTML = `<a href="${{stored}}" target="_blank">internal</a> <button class="edit-link">edit</button>`;
    }} else {{
      span.innerHTML = `<button class="add-link">add internal link</button>`;
    }}
  }});
}}
refreshLinks();

document.body.addEventListener('click', ev => {{
  if (ev.target.classList.contains('add-link') || ev.target.classList.contains('edit-link')) {{
    const span = ev.target.parentElement;
    const url = span.dataset.url;
    const current = localStorage.getItem('internal-' + url) || '';
    const link = prompt('Enter internal link URL:', current);
    if (link !== null) {{
      if (link) {{
        localStorage.setItem('internal-' + url, link);
      }} else {{
        localStorage.removeItem('internal-' + url);
      }}
      refreshLinks();
    }}
  }}
}});
</script>
</body>
</html>
"""
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate interactive docs hierarchy HTML")
    parser.add_argument('--taxonomy', default='dynatrace_fast_taxonomy.json', help='Path to taxonomy JSON file')
    parser.add_argument('--output', default='docs_hierarchy.html', help='Output HTML file')
    args = parser.parse_args()

    taxonomy_path = Path(args.taxonomy)
    if not taxonomy_path.is_file():
        raise SystemExit(f"Taxonomy file not found: {taxonomy_path}")

    with taxonomy_path.open() as f:
        data = json.load(f)

    html = build_html(data)
    output_path = Path(args.output)
    output_path.write_text(html, encoding='utf-8')
    print(f"Generated {output_path}")

if __name__ == '__main__':
    main()
