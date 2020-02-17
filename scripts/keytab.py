import os.path
import subprocess
import threading
from datetime import datetime, timedelta

KEYTAB_FILE = None
principal = None


def set(name):
    """Tells the keytab module to look for the daemon/NAME.mit.edu
    keytab in ~/Private/NAME.keytab"""
    global KEYTAB_FILE, principal
    KEYTAB_FILE = os.path.expanduser("~/Private/%s.keytab" % name)
    principal = "daemon/%s.mit.edu" % name


def exists():
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
