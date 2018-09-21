import contextlib
import cookielib
import getpass
import urllib
import urllib2
import urlparse

from .model import meta


cookie_jar = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))


def ponyaddr():
    lockerdot = "%s." % getpass.getuser()
    if lockerdot == "pony.":
        lockerdot = ""
    return "pony@%sscripts.mit.edu" % (lockerdot,)


def call(url, **kwargs):
    data = [("user", ponyaddr()), ("pass", meta.Meta.get().pony_rt_pass)]

    if kwargs:
        data.append(
            (
                "content",
                "".join(
                    key + ": " + kwargs[key].replace("\n", "\n ") + "\n"
                    for key in sorted(kwargs)
                ),
            )
        )

    with contextlib.closing(
        opener.open(
            urlparse.urljoin("https://help.mit.edu/REST/1.0/", url),
            urllib.urlencode(data),
        )
    ) as f:
        return f.read()
