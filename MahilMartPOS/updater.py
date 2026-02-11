import os
import shutil
import time
import subprocess
import sys

BASE_DIR = r"C:\MahilMartPOS"
APP_DIR = os.path.join(BASE_DIR, "app")
OLD_EXE = os.path.join(APP_DIR, "MahilMartPOS.exe")
NEW_EXE = os.path.join(os.getcwd(), "MahilMartPOS.exe")
VERSION_FILE = os.path.join(os.getcwd(), "version.txt")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

os.makedirs(BACKUP_DIR, exist_ok=True)

print("Starting update...")

# 1️⃣ Backup database (PostgreSQL)
print("Backing up database...")
subprocess.call(
    'pg_dump -U mahilmart_user mahilmartdb > backups\\pre_update.sql',
    shell=True
)

time.sleep(2)

# 2️⃣ Replace EXE
if os.path.exists(OLD_EXE):
    os.remove(OLD_EXE)

shutil.copy(NEW_EXE, OLD_EXE)

# 3️⃣ Update version
shutil.copy(VERSION_FILE, BASE_DIR)

print("Update successful.")

# 4️⃣ Restart POS
os.startfile(OLD_EXE)
