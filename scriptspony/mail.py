import getpass

from scripts import mail


def ponyaddr(id):
    lockerdot = "%s." % getpass.getuser()
    if lockerdot == "pony.":
        lockerdot = ""
    return "pony+%s@%sscripts.mit.edu" % (id, lockerdot)


def create_ticket(subject, body, id, requestor):
    mail.create_ticket(subject, body, ponyaddr(id), requestor)


def send_comment(subject, body, id, rtid, fromaddr, toaddr=None):
    mail.send_comment(subject, body, ponyaddr(id), rtid, fromaddr, toaddr)


def send_correspondence(subject, body, rtid, fromaddr=None):
    if fromaddr is None:
        fromaddr = "scripts@mit.edu"
    mail.send_correspondence(subject, body, fromaddr, rtid)
