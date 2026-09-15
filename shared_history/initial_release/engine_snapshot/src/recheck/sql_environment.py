"""Executable, synthetic SQL tool world with stable schema and changing semantics.

This is a controlled adapter test, not a public benchmark or an LLM experiment.
The driver controls modes. The controller sees only calibrated probe receipts.
"""
import hashlib
import json
import sqlite3
import numpy as np


class SQLToolWorld:
    def __init__(self,seed: int):
        rng=np.random.default_rng(seed)
        self._base=rng.integers(1,1000,size=20).astype(float)/10
        self.conn=sqlite3.connect(':memory:')
        self.conn.executescript('CREATE TABLE orders(id INTEGER, amount REAL, event_time INTEGER);'
                               'CREATE TABLE calibration(id INTEGER, amount REAL, event_time INTEGER);')
        self.conn.executemany('INSERT INTO orders VALUES(?,?,?)',[(i,float(x),i) for i,x in enumerate(self._base)])
        self.conn.execute('INSERT INTO calibration VALUES(0,1,0)')
        self._unit=0; self._inclusive=0
        self.tool_calls=0
        self.receipts=[]
        self.initial_schema_fingerprint=self.schema_fingerprint()

    def __enter__(self): return self
    def __exit__(self,*args): self.conn.close()

    def schema_fingerprint(self)->str:
        rows=self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return hashlib.sha256(json.dumps(rows).encode()).hexdigest()

    def set_modes(self,unit: int,inclusive: int)->None:
        if unit not in (0,1) or inclusive not in (0,1): raise ValueError('binary modes required')
        self._unit=unit;self._inclusive=inclusive
        scale=100. if unit else 1.
        self.conn.executemany('UPDATE orders SET amount=? WHERE id=?',[(float(x*scale),i) for i,x in enumerate(self._base)])
        self.conn.execute('UPDATE calibration SET amount=?',(scale,))

    def _read(self,query:str,args:tuple=())->float:
        out=float(self.conn.execute(query,args).fetchone()[0]); self.tool_calls+=1
        self.receipts.append({'query':query,'args':list(args),'value':out})
        return out

    def probe(self,channel:int)->int:
        if channel==0:
            value=self._read('SELECT amount FROM calibration WHERE id=0')
            if value not in (1.,100.): raise ValueError('unsupported unit mode')
            return int(value==100.)
        if channel==1:
            op='<=' if self._inclusive else '<'
            count=self._read(f'SELECT COUNT(*) FROM calibration WHERE event_time {op} ?', (0,))
            return int(count)
        raise ValueError('invalid channel')

    def execute(self,task:int,cached_modes)->tuple:
        if task not in (0,1,2,3): raise ValueError('invalid task')
        out=[]
        if task in (0,2):
            total=self._read('SELECT SUM(amount) FROM orders')
            out.append(total/(100. if cached_modes[0] else 1.))
        if task in (1,2):
            # Public task: event_time <= 10. Tool bound semantics are uncertain.
            bound=10 if cached_modes[1] else 11
            op='<=' if self._inclusive else '<'
            out.append(self._read(f'SELECT COUNT(*) FROM orders WHERE event_time {op} ?', (bound,)))
        if task==3: out.append(self.schema_fingerprint())
        return tuple(out)

    def evaluate(self,task:int,result:tuple)->bool:
        """Evaluator-only: never called by a refresh policy."""
        gold=[]
        if task in (0,2): gold.append(float(self._base.sum()))
        if task in (1,2): gold.append(11.)
        if task==3: return result==(self.initial_schema_fingerprint,)
        return len(result)==len(gold) and bool(np.allclose(result,gold,rtol=1e-10,atol=1e-10))
