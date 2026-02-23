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
    
# def get_client_ip(request):
#     x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#     if x_forwarded_for:
#         return x_forwarded_for.split(",")[0]
#     return request.META.get("REMOTE_ADDR", "")
    

# def get_machine_id(request):
#     """Reads machine-id sent from browser (UUID saved in localStorage)"""
#     return request.POST.get("machine_id") or "Unknown-Device"