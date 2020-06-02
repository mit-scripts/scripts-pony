#!/usr/bin/env python

from __future__ import print_function

from datetime import datetime, timedelta
import ldap
from OpenSSL import crypto
from scripts import cert, log, auth
from scriptspony import vhosts
import os
import sys
import logging


def pkey_to_pem(pk):
    return crypto.dump_publickey(crypto.FILETYPE_PEM, pk)


@log.exceptions
def main():
    pem = sys.stdin.read()
    replacement_certs = cert.pem_to_certs(pem)
    replacements = {pkey_to_pem(c.get_pubkey()): c for c in replacement_certs}

    logging.info("Replacement certificates: %s", replacements)

    vhosts.connect()
    res = vhosts.conn.search_s(
        "ou=VirtualHosts,dc=scripts,dc=mit,dc=edu",
        ldap.SCOPE_ONELEVEL,
        "(&(objectClass=scriptsVhost)(scriptsVhostCertificate=*))",
        ["scriptsVhostName", "scriptsVhostCertificate"],
    )

    for dn, attrs in res:
        replace = 0
        vhost, = attrs["scriptsVhostName"]
        logging.info("Examining %s", vhost)
        scripts, = attrs["scriptsVhostCertificate"]
        chain = cert.scripts_to_chain(scripts)
        for i, c in enumerate(chain):
            new = replacements.get(pkey_to_pem(c.get_pubkey()))
            if new:
                chain[i] = new
                replace += 1
        if replace:
            logging.info(
                "Replacing %d certificates for %s"
                % (replace, vhost)
            )
            try:
                vhosts.conn.modify_s(
                    dn,
                    [
                        (
                            ldap.MOD_REPLACE,
                            "scriptsVhostCertificate",
                            cert.chain_to_scripts(chain),
                        ),
                    ],
                )
            except ldap.INSUFFICIENT_ACCESS as e:
                logging.exception(e)


if __name__ == "__main__":
    auth.set_user_from_parent_process()
    from paste.deploy import loadapp

    loadapp("config:development.ini", relative_to=os.path.dirname(__file__))
    logging.basicConfig(level=logging.DEBUG)
    main()
