# Dynatrace Docs Hierarchy Generator

This repo contains a small script that crawls the public Dynatrace documentation site and generates an interactive HTML page listing the hierarchy of topics. Each entry links back to the official vendor documentation as well as a placeholder link for internal documentation.

## Requirements

- Python 3.12+
- `requests` and `beautifulsoup4` (`pip install requests beautifulsoup4`)

## Usage

Run the following command:

```bash
python generate_docs_hierarchy.py
```

The script retrieves the Dynatrace documentation pages starting from `https://docs.dynatrace.com/docs`, builds a nested structure, and then writes:

- `docs_hierarchy.json` – a JSON representation of the hierarchy
- `docs_hierarchy.html` – an interactive webpage using HTML `<details>` elements

Open `docs_hierarchy.html` in your browser to explore the hierarchy.

## Limitations

This script requires network access to `docs.dynatrace.com`. If network access is blocked or the domain is unreachable, the script will fail. The placeholder `[internal]` links in the generated HTML can be replaced with links to your organization's internal documentation.
