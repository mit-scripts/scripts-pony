import subprocess
import threading
from decorator import decorator
import pwd, os
import re
import cgi

import webob.exc

from . import keytab, log
from .model import meta

state = threading.local()


def html(s):
    return "<html>" + s


import sys, tg.flash

# Monkeypatch to prevent webflash from escaping HTML conditionally
sys.modules["tg.flash"].escape = (
    lambda s: s[len("<html>") :] if s.startswith("<html>") else cgi.escape(s)
)


def current_user():
    return getattr(state, "username", None)


def is_https():
    return state.https


def is_sudoing():
    return getattr(state, "sudo", False)


def first_name():
    fullname = state.name
    bits = fullname.split()
    if len(bits) > 0:
        return bits[0]
    else:
        return None


def can_admin(locker):
    """Return true if the authentiated user can admin the named locker."""
    if not current_user():
        return False
    if not keytab.exists():
        cmd = ["/usr/local/bin/admof", "-noauth", locker, current_user()]
    else:
        # This quoting is safe because we've already ensured locker
        # doesn't contain dumb characters
        cmd = [
            "/usr/bin/pagsh",
            "-c",
            "aklog athena sipb zone && /usr/local/bin/admof '%s' '%s'"
            % (locker, current_user()),
        ]
    admof = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = admof.communicate()
    if admof.returncode not in (33, 1):

        raise OSError(admof.returncode, err)
    if out.strip() not in ("", "yes", "no") or err.strip() not in (
        "",
        "internal error: pioctl: No such file or directory",
    ):
        log.err(
            "admof failed for %s/%s: out='%s', err='%s'"
            % (locker, current_user(), out.strip(), err.strip())
        )
    return out.strip() == "yes" and admof.returncode == 33


class AuthError(webob.exc.HTTPForbidden):
    pass


LOCKER_PATTERN = re.compile(r"^(?:\w[\w.-]*\w|\w)$")


def validate_locker(locker, team_ok=False, sudo_ok=False):
    if not LOCKER_PATTERN.search(locker):
        raise AuthError("'%s' is not a valid locker." % locker)
    else:
        try:
            pwd.getpwnam(locker)
        except KeyError:
            raise AuthError(
                html(
                    """The '%s' locker is not signed up for scripts.mit.edu; <a href="http://scripts.mit.edu/web/">sign it up</a> first."""
                    % cgi.escape(locker)
                )
            )
        if (
            (not team_ok or not on_scripts_team())
            and (not sudo_ok or not getattr(state, "sudo", False))
            and not can_admin(locker)
        ):
            raise AuthError(
                "You cannot administer the '%s' locker! Please see http://scripts.mit.edu/faq/159 for more details."
                % locker
            )


@decorator
def sensitive(func, locker, *args, **kw):
    """Wrap a function that takes a locker as the first argument
    such that it throws an AuthError unless the authenticated
    user can admin that locker."""
    validate_locker(locker)
    return func(locker.lower(), *args, **kw)


@decorator
def team_sensitive(func, locker, *args, **kw):
    """Wrap a function that takes a locker as the first argument
    such that it throws an AuthError unless the authenticated
    user can admin that locker or is on scripts-pony-acl."""
    validate_locker(locker, team_ok=True)
    return func(locker.lower(), *args, **kw)


@decorator
def sudo_sensitive(func, locker, *args, **kw):
    """Wrap a function that takes a locker as the first argument
    such that it throws an AuthError unless the authenticated
    user can admin that locker or is on scripts-pony-acl and actively
    trying to sudo."""
    validate_locker(locker, sudo_ok=True)
    return func(locker.lower(), *args, **kw)


class ScriptsAuthMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        state.username = environ.get("REMOTE_USER", None)
        # We don't use SERVER_PORT because that lies and says 443 for
        # some reason
        state.sudo = None
        state.https = environ.get("HTTP_HOST", "").endswith(":444")
        state.name = environ.get("SSL_CLIENT_S_DN_CN", "")
        if keytab.exists():
            keytab.auth()
        return self.app(environ, start_response)


def on_scripts_team():
    if not current_user():
        return False
    # Treat procmail/cron as scripts team
    if current_user().startswith("!"):
        return True
    if not keytab.exists():
        cmd = ["pts", "memb", "system:scripts-pony-acl", "-noauth"]
    else:
        cmd = [
            "/usr/bin/pagsh",
            "-c",
            "aklog && pts memb system:scripts-pony-acl -encrypt",
        ]
    pts = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pts.communicate()
    teamers = (n.strip() for n in out.strip().split("\n")[1:])
    return current_user() in teamers


def scripts_team_sudo():
    """If the user is on scripts team, give them a few extra bits;
    otherwise, raise AuthError."""
    if on_scripts_team():
        state.sudo = True
    else:
        raise AuthError("You are not on Scripts Team!")


def set_user_from_parent_process():
    cmdline = file("/proc/%s/cmdline" % os.getppid()).read()
    state.username = "!" + cmdline.split("\x00")[0]


def token():
    return meta.Meta.token_for_user(current_user())
