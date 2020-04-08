#!/usr/bin/env python

import email
import sys
import ldap
import ldap.filter
from scripts import cert, log, auth
from scriptspony import vhosts

BLACKLIST = ["scripts.mit.edu", "notfound.example.com"]


@log.exceptions
def main():
    if hasattr(sys.stdin, "buffer"):
        msg = email.message_from_binary_file(sys.stdin.buffer)
    else:
        msg = email.message_from_file(sys.stdin)
    pem = cert.msg_to_pem(msg)
    if pem is None:
        log.info("handle_cert_mail.py: No certificate")
        return
    chain = cert.pem_to_chain(pem)
    names = cert.chain_subject_names(chain)

    filter = ldap.filter.filter_format(
        "(&(objectClass=scriptsVhost)(|"
        + "".join("(scriptsVhostName=%s)" for name in names)
        + "".join("(scriptsVhostAlias=%s)" for name in names)
        + ")"
        + "".join("(!(scriptsVhostName=%s))" for name in BLACKLIST)
        + ")",
        list(names) + list(names) + BLACKLIST,
    )

    vhosts.connect()
    res = vhosts.conn.search_s(
        "ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",
        ldap.SCOPE_ONELEVEL,
        filter,
        ["scriptsVhostName", "scriptsVhostAccount", "scriptsVhostCertificate"],
    )
    if res:
        for dn, attrs in res:
            vhost, = attrs["scriptsVhostName"]
            account, = attrs["scriptsVhostAccount"]
            if "scriptsVhostCertificate" in attrs:
                old_scripts, = attrs["scriptsVhostCertificate"]
                old_chain = cert.scripts_to_chain(old_scripts)
            else:
                old_chain = None
            if cert.chain_should_install(chain, old_chain):
                log.info(
                    "handle_cert_mail.py: Installing certificate for %s on %s"
                    % (vhost, account)
                )
                vhosts.conn.modify_s(
                    dn,
                    [
                        (
                            ldap.MOD_REPLACE,
                            "scriptsVhostCertificate",
                            cert.chain_to_scripts(chain),
                        ),
                        (
                            ldap.MOD_REPLACE,
                            "scriptsVhostCertificateKeyFile",
                            "scripts-2048.key",
                        ),
                    ],
                )
            else:
                log.info(
                    "handle_cert_mail.py: IGNORING certificate for %s on %s"
                    % (vhost, account)
                )
    else:
        log.error(
            "handle_cert_mail.py: Certificate for %s matches no vhost" % list(names)
        )


if __name__ == "__main__":
    auth.set_user_from_parent_process()
    main()
