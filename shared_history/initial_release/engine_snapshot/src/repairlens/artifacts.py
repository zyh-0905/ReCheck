"""Local, content- and input-bound replay artifacts. No external effects rollback.

Digests detect accidental mismatch, not a malicious host capable of rewriting
both content and metadata. Reuse also requires the caller's semantic contract.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil


def canonical_bytes(value)->bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


class ArtifactStore:
    def __init__(self,path):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True)

    def _path(self,key:str)->Path:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',key): raise ValueError('invalid artifact key')
        return self.path/(key+'.json')

    def put(self,key:str,payload:dict,input_digest:str)->None:
        envelope={'payload':payload,'input_digest':input_digest,
                  'payload_sha256':hashlib.sha256(canonical_bytes(payload)).hexdigest()}
        target=self._path(key); tmp=target.with_suffix('.tmp')
        tmp.write_bytes(canonical_bytes(envelope));os.replace(tmp,target)

    def get(self,key:str,input_digest:str)->dict:
        try:
            e=json.loads(self._path(key).read_text())
            if e['input_digest']!=input_digest: raise ValueError('input digest mismatch')
            if hashlib.sha256(canonical_bytes(e['payload'])).hexdigest()!=e['payload_sha256']:
                raise ValueError('content digest mismatch')
            return e['payload']
        except (KeyError,json.JSONDecodeError) as exc: raise ValueError('invalid artifact envelope') from exc

    def snapshot(self,target)->Path:
        target=Path(target)
        if self.path.resolve() in target.resolve().parents or self.path.resolve()==target.resolve():
            raise ValueError('snapshot must be outside active directory')
        shutil.copytree(self.path,target,dirs_exist_ok=True)
        return target

    def restore(self,snapshot)->None:
        snapshot=Path(snapshot)
        if not snapshot.is_dir() or snapshot.resolve()==self.path.resolve():raise ValueError('invalid snapshot')
        shutil.rmtree(self.path)
        shutil.copytree(snapshot,self.path)

    def digest(self)->str:
        h=hashlib.sha256()
        for p in sorted(self.path.glob('*.json')): h.update(p.name.encode());h.update(p.read_bytes())
        return h.hexdigest()
