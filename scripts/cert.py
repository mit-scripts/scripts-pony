import base64
from datetime import datetime
import re
from OpenSSL import crypto
import pyasn1.codec.der.decoder as der_decoder
from pyasn1_modules.rfc2459 import SubjectAltName
import requests

SCRIPTS_PUBKEY = base64.b64decode(
    """\
MIIBDQIBAAKCAQEAxJo8HD63ei1mpkNGQVv3wXXGrQUiDON1FhsJ6iYiCFmxmOKNvFssPlQ48uIB
JBNCqLh8EkmnmecSI5kDPlDGy/rq2lZC7OrSfcsNzTP9fXHi5kvYoOS6XuVuLf/yDglp7T/7qcrM
PXX4KBDcaILnEH9Y8Leg8UBVf2xGgSF+Pe62oTR7BX8+g9TUUp6pdycdwr6JCwJaRKnokys2CksY
yOlVdOZByV0ZVHZjVC4uOwn72GfLJEdni7wYZ76tgWXW2c1l3j09wL47BfBtDq3W9STke5HS2SRv
Wh/U2tDLIzO+mzBR1mrkk+gs8XGC919jFXQzBqDNrmUmrtT6YrSAHwIDAQAB
"""
)


def pem_to_chain(data):
    certs = [
        crypto.load_certificate(crypto.FILETYPE_PEM, m.group(0))
        for m in re.finditer(
            b"-----BEGIN CERTIFICATE-----\r?\n.+?\r?\n-----END CERTIFICATE-----",
            data,
            re.DOTALL,
        )
    ]

    # Put the chain in the right order, and delete any self-signed root
    leaf, = [
        c for c in certs if not any(c1.get_issuer() == c.get_subject() for c1 in certs)
    ]
    chain = [leaf]
    count = 1
    while True:
        issuers = [c for c in certs if chain[-1].get_issuer() == c.get_subject()]
        if not issuers:
            break
        issuer, = issuers
        assert issuer not in chain
        count += 1
        if issuer.get_issuer() == issuer.get_subject():
            break
        chain.append(issuer)
    assert count == len(certs)

    return chain


def chain_to_scripts(chain):
    return b" ".join(
        base64.b64encode(crypto.dump_certificate(crypto.FILETYPE_ASN1, c))
        for c in chain
    )


def scripts_to_chain(data):
    return [
        crypto.load_certificate(crypto.FILETYPE_ASN1, base64.b64decode(d))
        for d in data.split(b" ")
    ]


def chain_to_pem(chain):
    return b"".join(crypto.dump_certificate(crypto.FILETYPE_PEM, c) for c in chain)


def chain_subject_names(chain):
    names = {
        name for field, name in chain[0].get_subject().get_components() if field == "CN"
    }
    for i in range(chain[0].get_extension_count()):
        ext = chain[0].get_extension(i)
        if ext.get_short_name() == "subjectAltName":
            value, substrate = der_decoder.decode(
                ext.get_data(), asn1Spec=SubjectAltName()
            )
            assert substrate == b""
            for component in value:
                if component.getName() == "dNSName":
                    names.add(str(component.getComponent()))
    return names


def chain_notAfter(chain):
    return min(datetime.strptime(c.get_notAfter(), "%Y%m%d%H%M%SZ") for c in chain)


def chain_should_install(new_chain, old_chain=None):
    if (
        crypto.dump_privatekey(crypto.FILETYPE_ASN1, new_chain[0].get_pubkey())
        != SCRIPTS_PUBKEY
    ):
        return False

    if old_chain and not chain_notAfter(new_chain) > chain_notAfter(old_chain):
        return False

    if old_chain and not chain_subject_names(new_chain).issuperset(
        chain_subject_names(old_chain)
    ):
        return False

    # TODO actually verify the chain, once we have PyOpenSSL 0.15

    return True


def msg_to_pem(msg):
    urls = set(
        re.findall(
            r"https://cert-manager\.com/customer/InCommon/ssl\?action=download&sslId=\d+&format=x509",
            msg,
        )
    )
    if not urls:
        return None
    url, = urls
    r = requests.get(url)
    return r.text if r.status_code == 200 else None
