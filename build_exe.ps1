$ErrorActionPreference = "Stop"

python -m pip install --upgrade pip pyinstaller

python -m PyInstaller --clean --noconfirm MahilMartPOS.spec
