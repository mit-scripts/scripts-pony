import os.path
import subprocess
import threading
from datetime import datetime, timedelta

from tg import config

KEYTAB_FILE = None
principal = None


def set(keytab_file, k5principal):
    """Tells the keytab module to look for the k5principal
    keytab in keytab_file"""
    global KEYTAB_FILE, principal
    KEYTAB_FILE = os.path.expanduser(keytab_file)
    principal = k5principal


def exists():
    if not KEYTAB_FILE:
        set(config.get('keytab'), config.get('principal'))
    return os.path.exists(KEYTAB_FILE)


state = threading.local()


def auth():
    now = datetime.now()
    if not hasattr(state, "got_tickets") or now - state.got_tickets < timedelta(
        hours=10
    ):
        if os.path.exists("/usr/kerberos/bin/kinit"):
            kinit = "/usr/kerberos/bin/kinit"
        else:
            kinit = "/usr/bin/kinit"
        subprocess.Popen([kinit, principal, "-k", "-t", KEYTAB_FILE]).wait()
        state.got_tickets = now
