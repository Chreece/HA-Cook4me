"""Load the real ES-module graph locally, without a server or network access."""
from pathlib import Path
import base64
import json
import mimetypes
import posixpath
import re

IMPORT = re.compile(r'''(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s*)(["'])(\.[^"']+)\1''')
ASSET = re.compile(r'''new URL\(\s*(["'])(\.[^"']+)\1\s*,\s*import\.meta\.url\s*\)\.href''')

def local_html(root: Path) -> str:
    entry='custom_components/cook4me/frontend/cook4me-panel-v180.js'
    todo=[entry]
    sources={}
    while todo:
        path=todo.pop()
        if path in sources:
            continue
        source=(root/path).read_text()
        def reference(match):
            target=posixpath.normpath(posixpath.join(posixpath.dirname(path),match[2].split('?',1)[0]))
            if not target.startswith('custom_components/cook4me/frontend/'):
                raise AssertionError('Module outside frontend: '+target)
            todo.append(target)
            return match[0].replace(match[2],'ui203/'+target)
        source=IMPORT.sub(reference,source)
        def asset(match):
            target=root/posixpath.normpath(posixpath.join(posixpath.dirname(path),match[2].split('?',1)[0]))
            content=target.read_bytes()
            mime=mimetypes.guess_type(target)[0] or 'application/octet-stream'
            return json.dumps('data:'+mime+';base64,'+base64.b64encode(content).decode())
        source=ASSET.sub(asset,source)
        source=source.replace('import.meta.url',json.dumps('https://fixture.invalid/'+path))
        sources[path]=source
    imports={'ui203/'+path:'data:text/javascript;base64,'+base64.b64encode(source.encode()).decode() for path,source in sources.items()}
    html=(root/'tests/ui_refresh_fixture_v203.html').read_text()
    html=html.replace("'../"+entry+"'", "'ui203/"+entry+"'")
    # about:blank has opaque-origin storage; this isolated in-memory store is the
    # browser-storage boundary, not production persistence code.
    html=html.replace('<script type="module">','<script type="importmap">'+json.dumps({'imports':imports})+'</script><script type="module">\nconst testStorage=new Map();Object.defineProperty(window,"localStorage",{value:{getItem:k=>testStorage.get(k)||null,setItem:(k,v)=>testStorage.set(k,v),removeItem:k=>testStorage.delete(k),clear:()=>testStorage.clear()}});')
    return html
