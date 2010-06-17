import socket, dns.resolver

def points_at_scripts(hostname):
    """Return whether the hostname has the same IP as scripts-vhosts."""
    scriptsvhosts = socket.gethostbyname("scripts-vhosts.mit.edu.")
    try:
        for addr in (answer.address for answer in dns.resolver.query(hostname+'.', 'A')):
            if addr != scriptsvhosts:
                return False
    except dns.resolver.NXDOMAIN:
        return False
    except dns.resolver.NoAnswer:
        return False
    return True
