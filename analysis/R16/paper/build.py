"""Compile local LaTeX only. Requires pdflatex; no downloads or model requests."""
from pathlib import Path
import shutil,subprocess,sys
root=Path(__file__).resolve().parent
if not shutil.which('pdflatex'):
    raise SystemExit('pdflatex is missing. Open main.tex in an existing TeX installation or Overleaf.')
target='main.tex' if len(sys.argv)==1 else sys.argv[1]
if target not in {'main.tex','author_manuscript.tex'}:raise SystemExit('Choose main.tex or author_manuscript.tex')
for _ in range(2):
    subprocess.run(['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error',target],cwd=root,check=True)
print(root/target.replace('.tex','.pdf'))
