$ErrorActionPreference = "Stop"

python -m pip install --upgrade pip pyinstaller

python -m PyInstaller --clean --noconfirm --onefile --noconsole --name MahilMartPOS `
  --collect-all django `
  --collect-all barcode `
  --add-data "db.sqlite3;db.sqlite3" `
  --add-data "MahilMartPOS_App\\templates;MahilMartPOS_App\\templates" `
  --add-data "staticfiles;staticfiles" `
  --add-data "MahilMartPOS;MahilMartPOS" `
  --add-data "MahilMartPOS_App;MahilMartPOS_App" `
  app_launcher.py
