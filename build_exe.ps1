$ErrorActionPreference = "Stop"

python -m pip install --upgrade pip pyinstaller pymongo dnspython

python -m PyInstaller --clean --noconfirm MahilMartPOS.spec
