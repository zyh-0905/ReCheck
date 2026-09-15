#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v pdflatex >/dev/null || { echo 'pdflatex is required.' >&2; exit 1; }
command -v pdffonts >/dev/null || { echo 'pdffonts (Poppler) is required for audit.' >&2; exit 1; }
python scripts/make_report.py
cp figures/recheck_frontier.pdf figures/recheck_drift.pdf papers/recheck/figures/
cp figures/repairlens_families.pdf figures/repairlens_latency_model.pdf papers/repairlens/figures/
for paper in recheck repairlens; do
  (cd "papers/$paper" && pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null && pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null)
done
python scripts/audit.py
