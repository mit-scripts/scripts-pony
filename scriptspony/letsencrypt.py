import tempfile
import subprocess
import base64
from datetime import datetime, timedelta
from dateutil import parser
import pytz

import vhosts
import acme_tiny

from scripts import log


ACCOUNT_KEY = '/afs/athena.mit.edu/contrib/scripts/REPLACEME/account.key'  # TODO: make an account key
ACME_DIR = '/afs/athena.mit/edu/contrib/scripts/REPLACEME'  # TODO: decide an acme_dir or another way of storing responses to challenges
ACME_CA = acme_tiny.STAGING_CA
# ACME_CA = acme_tiny.PRODUCTION_CA




def request_and_install(locker, hostname, aliases):
    """ request_and_install contacts the Let's Encrypt servers, performs an authentication,
        requests a certificate for @hostname, and installs it in LDAP."""
    
    # TODO: check that this hostname actually points at scripts right now?
    csr_req_cmd = ['/bin/sudo', '/etc/pki/tls/gencsr-pony',locker,hostname]

    for alias in aliases:
        csr_req_cmd.append(alias)

    csr_req = subprocess.Popen(csr_req_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = csr_req.communicate()
    if csr_req.returncode:
        raise vhosts.UserError("CSR Request Failed: %s" % err)
    else:
        csr_contents = out
        csr_file = tempfile.NamedTemporaryFile()
        # write csr_contents to csr_file
        csr_file.write(csr_contents)

        # call acme_tiny.py with the CSR
        cert = acme_tiny.get_crt(ACCOUNT_KEY, csr_file.name(), ACME_DIR, log=acme_tiny.LOGGER, CA=ACME_CA)
        csr_file.close() 

        # download the intermediate cert
        intermediate_cert_location = "https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem"
        intermediate_cert = urlopen(intermediate_cert_location).read()
        certs = cert + "\n" + intermediate_cert
        
        # import the cert into scripts
        # exceptions will bubble up and be caught by caller.
        vhosts.set_cert(locker, hostname, importcert)
           

@log.exceptions
def examine_all_for_renewal():
    from OpenSSL import crypto
    
    output = ""
    # get the certs for all the hosts (locker,vhost,aliases,cert)
    vhost_list = vhosts.list_all_vhosts_with_certs()
    output += str(vhost_list)
    output += "\n---------------------------------------------------\n"
    
    # look at each one and look at the issuer and the expiration date
    for locker,vhost,aliases,certstr in vhost_list:
        certs = [crypto.load_certificate(crypto.FILETYPE_ASN1, base64.b64decode(cert)) for cert in certstr.split()]
        direct_cert = certs[0]
        issuer = direct_cert.get_issuer()
        if issuer.get_components() != [('C', 'US'), ('O', "Let's Encrypt"), ('CN', "Let's Encrypt Authority X3")]:
            # not an LE cert
            continue
        notAfter = parser.parse(direct_cert.get_notAfter())
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        time_until_expiry = notAfter - now
        already_expired = time_until_expiry < timedelta(days=0)
        # TODO: should we renew expired certs?
        
        if time_until_expiry > timedelta(days=30):
            # no need to renew
            continue
        
        names = []
        altNameData = ''
        for extno in xrange(direct_cert.get_extension_count()):
            ext = direct_cert.get_extension(extno)
            if ext.get_short_name() == 'subjectAltName':
                altNameData = ext.get_data()
                break
        
        if not altNameData:
            # subjectAltName should be present in modern certs, we should never reach this point.
            print "Warning - couldn't parse cert for vhost %s but it is expiring within 30 days" % vhost
            continue
        
        vhost_in_list = False
        
        # TODO: write magic_parse_asn1. I spent over an hour trying to do that and gave up.
        # I want my https://golang.org/pkg/encoding/asn1/ back.
        # maybe https://stackoverflow.com/questions/5519958/how-do-i-parse-subjectaltname-extension-data-using-pyasn1 will help.
        # or maybe from ndg.httpsclient.subj_alt_name import SubjectAltName but that adds a dependency
        def magic_parse_asn1(subjectAltName):
            return ["www.google.com"]
        
        for name in magic_parse_asn1(altNameData):
            if name in aliases:
                names.append(name)
            elif name == vhost:
                vhost_in_list = True
        
        if vhost_in_list:
            # TODO: something to stop this from trying and failing to renew the same cert every 12 hours
            try:
                request_and_install(locker, vhost, names)
                print "Successfully renewed certificate for %s" % vhost
            except UserError,e:
                print "Error - failed to renew certificate for vhost %s - error: %s" % (vhost, e.message)
            
        
        
    
    
if __name__ == "__main__":
    # TODO: this probably causes problems w/r/t auth when doing vhosts stuff.
    examine_all_for_renewal()
    