import os.path
import subprocess

KEYTAB_FILE = os.path.expanduser("~/Private/scripts-pony.keytab")

def exists():
    return os.path.exists(KEYTAB_FILE)

def auth():
    subprocess.Popen(['/usr/kerberos/bin/kinit','daemon/scripts-pony.mit.edu',
                      '-k','-t', KEYTAB_FILE]).wait()
