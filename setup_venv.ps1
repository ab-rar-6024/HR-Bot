# One-time setup:  powershell -ExecutionPolicy Bypass -File setup_venv.ps1
# Serving only:    .venv\Scripts\pip install -r requirements.txt
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
# CPU-only torch (small). On a GPU box drop --index-url.
.\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\pip install -r requirements-dev.txt
Write-Host "Activate with:  .\.venv\Scripts\Activate.ps1"
