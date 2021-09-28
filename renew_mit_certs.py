#!/usr/bin/env python

from __future__ import print_function

import os
import socket
import subprocess
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from paste.deploy import appconfig
import ldap
from scripts import cert
from scriptspony import vhosts
from scriptspony.config.environment import load_environment

NON_SCRIPTS_VHOSTS_ALIAS = ["sipb.mit.edu"]

def get_expiring_certs():
    """
    Most of this function is from find_expiring_certs.py
    """
    # load turbogears config, required for vhosts.connect to work
    config = appconfig('config:' + os.path.abspath('development.ini'))
    load_environment(config.global_conf, config.local_conf)

    now = datetime.utcnow()

    vhosts.connect()
    res = vhosts.conn.search_s(
        "ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",
        ldap.SCOPE_ONELEVEL,
        "(&(objectClass=scriptsVhost)(scriptsVhostCertificate=*))",
        [
            "scriptsVhostName", "scriptsVhostAlias", "uid",
            "scriptsVhostCertificate"
        ],
    )

    expiring = []
    for _, attrs in res:
        vhost, = attrs["scriptsVhostName"]
        aliases = attrs.get("scriptsVhostAlias", [])
        uid, = attrs["uid"]
        scripts, = attrs["scriptsVhostCertificate"]
        chain = cert.scripts_to_chain(scripts)
        expires = cert.chain_notAfter(chain) - now
        if expires < timedelta(days=14):
            expiring.append((expires, uid, [vhost] + aliases))
    expiring.sort()
    return expiring


def renew_expiring_mit_certs():
    expiring = get_expiring_certs()
    for _, uid, hostnames in expiring:
        mit_hostnames = [h for h in hostnames if not ('.' in h and not 'mit.edu' in h)]
        if 'mit.edu' in hostnames[0]:
            try:
                hostnames = request_cert(uid, mit_hostnames)
                print("CSR sent for " + ", ".join(hostnames))
            except (AssertionError, IOError, OSError) as err:
                print("failed to send CSR for " + ", ".join(hostnames) + ": ",
                      err)


def request_cert(locker, hostnames):
    """
    The code from send_mitcert_request.py, but as a function
    """
    for i, hostname in enumerate(hostnames):
        hostname = hostname.lower()
        if not hostname.endswith(".mit.edu"):
            hostname += ".mit.edu"
        assert hostname.endswith(".mit.edu"), hostname
        if hostname not in NON_SCRIPTS_VHOSTS_ALIAS:
            assert socket.gethostbyname(hostname) == "18.4.86.46", hostname
        hostnames[i] = hostname
    hostnames = list(set(hostnames))
    csr = subprocess.check_output(
        ["sudo", "/etc/pki/tls/gencsr-pony", locker] + hostnames)
    assert csr.startswith("-----BEGIN CERTIFICATE REQUEST-----\n")

    msg = MIMEText("""\
At your convenience, please sign this certificate for
{hostnames} (an alias of scripts-vhosts).

Thanks,
SIPB Scripts team

{csr}
""".format(hostnames=", ".join(hostnames), csr=csr))
    msg["From"] = "scripts-tls@mit.edu"
    msg["To"] = "mitcert@mit.edu"
    msg["Cc"] = "scripts-root@mit.edu"
    msg["Subject"] = "Certificate signing request for " + ", ".join(hostnames)

    p = subprocess.Popen(["/usr/sbin/sendmail", "-t", "-oi"],
                         stdin=subprocess.PIPE)
    p.communicate(msg.as_string())
    return hostnames


if __name__ == "__main__":
    renew_expiring_mit_certs()
