# Dynatrace Docs Hierarchy Generator

This repo contains a small script that crawls the public Dynatrace documentation site and generates an interactive HTML page listing the hierarchy of topics. The crawler recursively follows links within the Dynatrace docs to build a nested tree. Each entry links back to the official vendor documentation as well as a placeholder link for internal documentation.

## Requirements

- Python 3.12+
- `requests` and `beautifulsoup4` (`pip install requests beautifulsoup4`)
- `Flask` and `Flask-CORS` if you want to use the optional storage server

## Usage

Run the following command to crawl the live documentation site (requires Selenium and network access):

```bash
python generate_docs_hierarchy.py
```

If you already have a predefined taxonomy (for example `dynatrace_fast_taxonomy.json`), you can generate the hierarchy offline:

```bash
python generate_docs_hierarchy.py --taxonomy dynatrace_fast_taxonomy.json --output docs_hierarchy.html
```

The script retrieves the Dynatrace documentation pages starting from `https://docs.dynatrace.com/docs`, builds a nested structure, and then writes:

- `docs_hierarchy.json` – a JSON representation of the hierarchy
- `docs_hierarchy.html` – an interactive webpage listing pages with placeholder internal links

Open `docs_hierarchy.html` in your browser to explore the hierarchy. The page stores any internal links you add in your browser's `localStorage`. Use the **Export Links** and **Import Links** buttons to save them to disk or load them back later.

### Using external storage

You can run a small Flask server to keep the internal links centrally so that every browser sees the same data. First install the dependencies and start the server:

```bash
pip install Flask Flask-CORS
python storage_server.py
```

Then generate the HTML pointing at the server:

```bash
python generate_docs_hierarchy.py --taxonomy dynatrace_fast_taxonomy.json \
  --output docs_hierarchy.html --server-url http://localhost:5000
```

When opened in the browser, the page will load and save links via that server instead of `localStorage`.

## Limitations

This script requires network access to `docs.dynatrace.com`. If network access is blocked or the domain is unreachable, the script will fail. The placeholder `[internal]` links in the generated HTML can be replaced with links to your organization's internal documentation.
