#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$ROOT_DIR/src"
cd "$ROOT_DIR"

py -m streamlit run src/dashboard/streamlit_app.py \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#2dd4bf" \
    --theme.backgroundColor "#080c15" \
    --theme.secondaryBackgroundColor "#0d1422" \
    --theme.textColor "#dce5f0"
