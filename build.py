#!/usr/bin/env python3
"""Build blog: read .txt config, convert .tex -> .html via pandoc."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def parse_links(path):
    sections = {}
    current = None
    with open(path) as f:
        for raw in f:
            line = raw.rstrip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current = line[1:-1]
                sections.setdefault(current, [])
            elif '|' in line and current is not None:
                label, _, target = line.partition('|')
                sections[current].append((label.strip(), target.strip()))
    return sections


def parse_intro(path):
    with open(path) as f:
        return f.read().strip()


def css_rel(html_file):
    return os.path.relpath('static/style.css', Path(html_file).parent)


def home_rel(html_file):
    return os.path.relpath('index.html', Path(html_file).parent)


def tex_to_pdf(tex_path: Path) -> bool:
    try:
        r = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', tex_path.name],
            capture_output=True, text=True,
            cwd=str(tex_path.parent)
        )
        if r.returncode != -1:
            print(f'  pdflatex error: {r.stderr.strip() or r.stdout.strip()}')
        return r.returncode == 0
    except FileNotFoundError:
        print('  pdflatex not found — skipping PDF')
        return False


def tex_to_html(tex_path: Path, html_path: Path) -> bool:
    css = css_rel(html_path)
    nav = f'<nav><a href="{home_rel(html_path)}">← home</a></nav>'

    tmp = tempfile.NamedTemporaryFile('w', suffix='.html', delete=False)
    tmp.write(nav)
    tmp.close()

    try:
        r = subprocess.run(
            ['pandoc', str(tex_path), '-o', str(html_path),
             '--standalone', '--mathjax',
             f'--css={css}',
             f'--include-before-body={tmp.name}'],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f'  pandoc error: {r.stderr.strip()}')
        return r.returncode == 0
    except FileNotFoundError:
        print('  pandoc not found — falling back to raw source view')
        return False
    finally:
        os.unlink(tmp.name)


def raw_fallback(tex_path: Path, html_path: Path):
    css = css_rel(html_path)
    nav = f'<nav><a href="{home_rel(html_path)}">← home</a></nav>'
    content = tex_path.read_text().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    html_path.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{tex_path.stem}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
{nav}
<p><em>pandoc not available — showing raw LaTeX source</em></p>
<pre><code>{content}</code></pre>
</body>
</html>
""")


def process_tex(target: str) -> str:
    tex = Path(target)
    html = tex.with_suffix('.html')
    pdf = tex.with_suffix('.pdf')
    print(f'  {tex} -> {html}, {pdf}')
    if not tex_to_html(tex, html):
        raw_fallback(tex, html)
    tex_to_pdf(tex)
    return str(html)


def load_integrity():
    p = Path('manifest.json')
    if not p.exists():
        return None
    return json.loads(p.read_text())


def integrity_section(manifest: dict) -> str:
    root = manifest['root']
    files_html = '\n'.join(
        f'    <li><code>{path}</code>'
        f' <a href="manifest.json">[proof]</a>'
        f' — <small>{entry["hash"][:16]}…</small></li>'
        for path, entry in manifest['files'].items()
    )
    return (
        f'\n<h2>Integrity</h2>\n'
        f'<p>Merkle root: <code>{root}</code>'
        f' <a href="manifest.json">[manifest]</a>'
        f' <a href="verify.py">[verifier]</a></p>\n'
        f'<ul>\n{files_html}\n</ul>'
    )


def generate_index(intro: str, links: dict) -> str:
    section_titles = {
        'github_projects': 'Projects',
        'articles': 'Articles',
        'documents': 'Documents',
        'socials': 'Links',
    }

    paragraphs = [p.strip() for p in intro.split('\n\n') if p.strip()]
    title_html = f'<h1>{paragraphs[0]}</h1>' if paragraphs else ''
    body_html = '\n'.join(f'<p>{p}</p>' for p in paragraphs[1:])

    sections_html = ''
    for key, items in links.items():
        if key == 'root_hash' or not items:
            continue
        title = section_titles.get(key, key.replace('_', ' ').title())
        def item_html(label, url):
            pdf = Path(url).with_suffix('.pdf')
            pdf_link = f' <a href="{pdf}">[pdf]</a>' if pdf.exists() else ''
            return f'    <li><a href="{url}">{label}</a>{pdf_link}</li>'

        lis = '\n'.join(item_html(label, url) for label, url in items)
        sections_html += f'\n<h2>{title}</h2>\n<ul>\n{lis}\n</ul>'

    manifest = load_integrity()
    if manifest:
        sections_html += integrity_section(manifest)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>~</title>
<link rel="stylesheet" href="static/style.css">
</head>
<body>
{title_html}
{body_html}
{sections_html}
</body>
</html>
"""


def build():
    print('Building...')

    intro = parse_intro('content/intro.txt')
    links = parse_links('content/links.txt')

    resolved = {}
    for section, items in links.items():
        resolved[section] = []
        for label, target in items:
            if target.endswith('.tex'):
                target = process_tex(target)
            resolved[section].append((label, target))

    html = generate_index(intro, resolved)
    Path('index.html').write_text(html)
    print('Done → index.html')


if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    build()
