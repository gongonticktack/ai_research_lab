"""Download a licensed, single-person input; this does not run inference."""
import hashlib
import json
import urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=json.loads((root/'experiments/example-source.json').read_text(encoding='utf-8'))
destination=root/'private-data/image-001.jpg'
request=urllib.request.Request(source['download_url'],headers={'User-Agent':'AIResearchLab/1.0 (educational experiment setup)'})
with urllib.request.urlopen(request,timeout=60) as response:
    content=response.read(10*1024*1024+1)
if len(content)>10*1024*1024: raise ValueError('Example image too large')
if hashlib.sha1(content).hexdigest()!=source['publisher_sha1']: raise ValueError('Publisher image checksum mismatch')
if not content.startswith(b'\xff\xd8'): raise ValueError('Not a JPEG')
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_bytes(content)
print('Input saved:',destination)
print('SHA256:',hashlib.sha256(content).hexdigest())
print('Attribution:',source['author'],source['license'],source['source_page'])
