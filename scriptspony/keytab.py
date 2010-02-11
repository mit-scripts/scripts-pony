import os.path
import subprocess
import threading
from datetime import datetime, timedelta

KEYTAB_FILE = os.path.expanduser("~/Private/scripts-pony.keytab")

def exists():
    return os.path.exists(KEYTAB_FILE)

state = threading.local()

def auth():
    now = datetime.now()
    if (not hasattr(state,'got_tickets') 
        or now - state.got_tickets < timedelta(hours=10)):
        subprocess.Popen(['/usr/kerberos/bin/kinit',
                          'daemon/scripts-pony.mit.edu',
                          '-k','-t', KEYTAB_FILE]).wait()
        state.got_tickets = now
