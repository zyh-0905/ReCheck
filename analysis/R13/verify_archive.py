"""Verify manifest without network, executing research tools, or accessing keys."""
import hashlib,json,sys
from pathlib import Path

def verify(root):
    root=Path(root).resolve();manifest=json.loads((root/'MANIFEST.json').read_text());errors=[]
    for name,meta in manifest['files'].items():
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            errors.append({'file':name,'error':'unsafe path'});continue
        if not path.is_file():errors.append({'file':name,'error':'missing'});continue
        data=path.read_bytes()
        if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:
            errors.append({'file':name,'error':'digest or length mismatch'})
    return {'ok':not errors,'registered_files':len(manifest['files']),'errors':errors}

if __name__=='__main__':
    result=verify(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent)
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)
