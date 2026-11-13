"""Stamp a new version into index.html and version.json before pushing.

Browsers keep old copies of the app's files; the version is added to every
local file URL so a new release is always fetched fresh, and the running app
compares itself with version.json to offer an update.
Usage: python3 tools/bump_version.py
"""
import datetime
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parent.parent
v = datetime.datetime.now(datetime.timezone.utc).strftime('%Y.%m.%d-%H%M')
html = (root / 'index.html').read_text()
html = re.sub(r'(window\.RIGROOM_VERSION = )"[^"]*"', r'\1"%s"' % v, html)
html = re.sub(r'(\./src/[a-z]+\.(?:js|css))\?v=[^"]*"', r'\1?v=%s"' % v, html)
(root / 'index.html').write_text(html)
(root / 'version.json').write_text(json.dumps({'version': v}) + '\n')
print(v)
