import socket

def points_at_scripts(hostname):
    """Return whether the hostname has the same IP as scripts-vhosts."""
    failed = False
    try:
        if (socket.gethostbyname(hostname+'.')
            != socket.gethostbyname("scripts-vhosts.mit.edu.")):
            failed=True
    except socket.gaierror:
        failed=True
    return not failed
