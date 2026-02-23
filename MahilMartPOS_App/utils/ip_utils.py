import socket

def get_computer_name_from_ip(ip):
    try:
        computer_name = socket.gethostbyaddr(ip)[0]
        return computer_name
    except:
        return "Unknown-PC"



import socket

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR", "")


def get_machine_name_from_ip(ip):
    try:
        name = socket.gethostbyaddr(ip)[0]
        return name.split('.')[0]      # remove domain
    except:
        return "Unknown-PC"




