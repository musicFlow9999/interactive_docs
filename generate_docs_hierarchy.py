#!/usr/bin/env python3
"""Generate interactive HTML from a Dynatrace taxonomy JSON file.

The generated HTML allows users to store custom internal links for each page.
Each link can have a custom name and description which are persisted in the
browser's localStorage. Optionally, links can be saved to and loaded from a
remote server if a storage URL is provided when generating the HTML.
"""
import json
import argparse
from pathlib import Path
from typing import Optional


def build_html(data: dict, server_url: Optional[str] = None) -> str:
    json_str = json.dumps(data)
    server_json = json.dumps(server_url) if server_url else 'null'
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
 .internal-link-list {{ margin-left: 1.5em; }}
 summary {{ cursor: pointer; font-weight: bold; }}
 button {{ margin-left: 4px; }}
 .description {{ color: #555; margin-left: 4px; }}
 #toolbar {{ margin-bottom: 1em; }}
</style>
</head>
<body>
 <h1>Dynatrace Documentation Hierarchy</h1>
 <div id="toolbar">
  <button id="export-links">Export Links</button>
  <button id="import-links">Import Links</button>
  <input type="file" id="import-file" style="display:none" accept="application/json">
 </div>
 <div id="tree"></div>
<script id="taxonomy-data" type="application/json">{json_str}</script>
<script>
const data = JSON.parse(document.getElementById('taxonomy-data').textContent);
const SERVER_URL = {server_json};
function createSection(section) {{
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = section.title;
  details.appendChild(summary);
  const ul = document.createElement('ul');
  if (section.pages) {{
    section.pages.forEach(pg => {{
      const li = document.createElement('li');
      li.innerHTML = `<div><a href="${{pg.url}}" target="_blank">${{pg.title}}</a>` +
                     `<span class="description"> - ${{pg.description}}</span></div>` +
                     `<ul class="internal-link-list" data-url="${{pg.url}}"></ul>`;
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
async function loadLinks(url) {{
  if (SERVER_URL) {{
    try {{
      const resp = await fetch(`${{SERVER_URL}}/links/${{encodeURIComponent(url)}}`);
      if (resp.ok) return await resp.json();
    }} catch (e) {{}}
    return [];
  }} else {{
    let stored = JSON.parse(localStorage.getItem("internal-" + url) || "[]");
    if (stored.length && typeof stored[0] === "string") {{
      stored = stored.map(l => ({{url: l, name: "", description: ""}}));
      localStorage.setItem("internal-" + url, JSON.stringify(stored));
    }}
    return stored;
  }}
}}

async function saveLinks(url, links) {{
  if (SERVER_URL) {{
    await fetch(`${{SERVER_URL}}/links/${{encodeURIComponent(url)}}`, {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(links)
    }});
  }} else {{
    if (links.length) {{
      localStorage.setItem("internal-" + url, JSON.stringify(links));
    }} else {{
      localStorage.removeItem("internal-" + url);
    }}
  }}
}}

async function refreshLinks() {{
  const lists = document.querySelectorAll(".internal-link-list");
  for (const ul of lists) {{
    const url = ul.dataset.url;
    const stored = await loadLinks(url);
    ul.innerHTML = "";
    stored.forEach((link, idx) => {{
      const li = document.createElement("li");
      const text = link.name || `internal ${{idx + 1}}`;
      const desc = link.description ? ` <span class="description">- ${{link.description}}</span>` : "";
      li.innerHTML = `<a href="${{link.url}}" target="_blank">${{text}}</a>${{desc}}` +
                     ` <button class="edit-link" data-index="${{idx}}">edit</button>` +
                     ` <button class="delete-link" data-index="${{idx}}">delete</button>`;
      ul.appendChild(li);
    }});
    const addLi = document.createElement("li");
    addLi.innerHTML = `<button class="add-link">add internal link</button>`;
    ul.appendChild(addLi);
  }}
}}
refreshLinks();


// Export links to a JSON file
document.getElementById('export-links').addEventListener('click', async () => {{
  let store = {{}};
  if (SERVER_URL) {{
    const resp = await fetch(`${{SERVER_URL}}/links`);
    if (resp.ok) {{
      store = await resp.json();
    }}
  }} else {{
    for (let i = 0; i < localStorage.length; i++) {{
      const key = localStorage.key(i);
      if (key && key.startsWith('internal-')) {{
        store[key.slice('internal-'.length)] = JSON.parse(localStorage.getItem(key));
      }}
    }}
  }}
  const blob = new Blob([JSON.stringify(store, null, 2)], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'internal-links.json';
  a.click();
  URL.revokeObjectURL(url);
}});

// Import links from a JSON file
document.getElementById('import-links').addEventListener('click', () => {{
  document.getElementById('import-file').click();
}});
document.getElementById('import-file').addEventListener('change', async ev => {{
  const file = ev.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async e => {{
    try {{
      const data = JSON.parse(e.target.result);
      if (SERVER_URL) {{
        await fetch(`${{SERVER_URL}}/links`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(data)
        }});
      }} else {{
        Object.entries(data).forEach(([url, links]) => {{
          localStorage.setItem('internal-' + url, JSON.stringify(links));
        }});
      }}
      await refreshLinks();
      alert('Links imported');
    }} catch(err) {{
      alert('Failed to import links: ' + err);
    }}
  }};
  reader.readAsText(file);
  ev.target.value = '';
}});

document.body.addEventListener('click', async ev => {{
  const ul = ev.target.closest('.internal-link-list');
  if (!ul) return;
  const url = ul.dataset.url;
  let stored = await loadLinks(url);

  if (ev.target.classList.contains('add-link')) {{
    const link = prompt('Enter internal link URL:');
    if (link) {{
      const name = prompt('Enter link name (optional):') || '';
      const desc = prompt('Enter link description (optional):') || '';
      stored.push({{url: link, name: name, description: desc}});
      await saveLinks(url, stored);
      await refreshLinks();
    }}
  }} else if (ev.target.classList.contains('edit-link')) {{
    const idx = parseInt(ev.target.dataset.index, 10);
    const current = stored[idx] || {{url: '', name: '', description: ''}};
    const link = prompt('Enter internal link URL:', current.url);
    if (link !== null) {{
      if (link) {{
        const name = prompt('Enter link name (optional):', current.name || '') || '';
        const desc = prompt('Enter link description (optional):', current.description || '') || '';
        stored[idx] = {{url: link, name: name, description: desc}};
      }} else {{
        stored.splice(idx, 1);
      }}
      await saveLinks(url, stored);
      await refreshLinks();
    }}
  }} else if (ev.target.classList.contains('delete-link')) {{
    const idx = parseInt(ev.target.dataset.index, 10);
    stored.splice(idx, 1);
    await saveLinks(url, stored);
    await refreshLinks();
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
    parser.add_argument('--server-url', help='Base URL of storage server')
    args = parser.parse_args()

    taxonomy_path = Path(args.taxonomy)
    if not taxonomy_path.is_file():
        raise SystemExit(f"Taxonomy file not found: {taxonomy_path}")

    with taxonomy_path.open() as f:
        data = json.load(f)

    html = build_html(data, server_url=args.server_url)
    output_path = Path(args.output)
    output_path.write_text(html, encoding='utf-8')
    print(f"Generated {output_path}")

if __name__ == '__main__':
    main()
