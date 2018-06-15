#!/usr/bin/env python

from __future__ import print_function

from datetime import datetime, timedelta
import ldap
from scripts import cert
from scriptspony import vhosts

def main():
    now = datetime.utcnow()

    res = vhosts.conn.search_s(
        'ou=VirtualHosts,dc=scripts,dc=mit,dc=edu',
        ldap.SCOPE_ONELEVEL,
        '(&(objectClass=scriptsVhost)(scriptsVhostCertificate=*))',
        ['scriptsVhostName', 'scriptsVhostAlias', 'uid', 'scriptsVhostCertificate'])

    expiring = []
    for dn, attrs in res:
        vhost, = attrs['scriptsVhostName']
        aliases = attrs.get('scriptsVhostAlias', [])
        uid, = attrs['uid']
        scripts, = attrs['scriptsVhostCertificate']
        chain = cert.scripts_to_chain(scripts)
        expires = cert.chain_notAfter(chain) - now
        if expires < timedelta(days=14):
            expiring.append((expires, uid, [vhost] + aliases))
    expiring.sort()
    for expires, uid, hostnames in expiring:
        print(expires, uid, *hostnames)

if __name__ == '__main__':
    main()
