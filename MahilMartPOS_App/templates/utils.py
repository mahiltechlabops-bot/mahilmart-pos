import os
import subprocess
from datetime import datetime

def backup_postgres_db(db_name, user, password, host, port, backup_dir):
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'{db_name}_backup_{timestamp}.sql')

    env = os.environ.copy()
    env["PGPASSWORD"] = password

    try:
        command = [
            'pg_dump',
            '-U', user,
            '-h', host,
            '-p', str(port),
            '-F', 'c',         
            '-f', backup_file,
            db_name
        ]

        subprocess.run(command, env=env, check=True)
        return True, f"Backup created: {backup_file}"
    except subprocess.CalledProcessError as e:
        return False, f"Backup failed: {e}"