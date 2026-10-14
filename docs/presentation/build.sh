#!/usr/bin/env bash
# Compila main.pdf y falla si pdflatex reportó errores ("!" al inicio de línea en main.log).
set -u
cd "$(dirname "$0")"
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > /dev/null 2>&1
status=$?
if [ $status -ne 0 ] || grep -q '^!' main.log; then
  echo "ERRORES en main.log:"
  grep -n -A3 '^!' main.log | head -40
  exit 1
fi
echo "ok: $(pdfinfo main.pdf 2>/dev/null | awk '/^Pages/ {print $2}') páginas"