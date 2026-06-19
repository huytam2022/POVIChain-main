@echo off
setlocal
set PYTHONPATH=%~dp0src
cd /d "%~dp0"

py -m streamlit run src\dashboard\streamlit_app.py ^
    --server.port 8501 ^
    --server.headless true ^
    --browser.gatherUsageStats false ^
    --theme.base dark ^
    --theme.primaryColor "#2dd4bf" ^
    --theme.backgroundColor "#080c15" ^
    --theme.secondaryBackgroundColor "#0d1422" ^
    --theme.textColor "#dce5f0"

endlocal
