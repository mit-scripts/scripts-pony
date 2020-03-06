# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, url, request, redirect

from scriptspony.lib.base import BaseController
from scriptspony.model import DBSession
from scriptspony.model.user import UserInfo
from scriptspony.controllers.error import ErrorController

from sqlalchemy.orm.exc import NoResultFound

from decorator import decorator
import subprocess
import cgi

from scripts import auth
from .. import rt, vhosts
from ..model import queue

__all__ = ["RootController"]

# Not in auth because it depends on TG
@decorator
def scripts_team_only(func, *args, **kw):
    if not auth.on_scripts_team():
        flash("You are not authorized for this area!")
        redirect("/")
    else:
        return func(*args, **kw)


class RootController(BaseController):
    """
    The root controller for the ScriptsPony application.
    
    All the other controllers and WSGI applications should be mounted on this
    controller. For example::
    
        panel = ControlPanelController()
        another_app = AnotherWSGIApplication()
    
    Keep in mind that WSGI applications shouldn't be mounted directly: They
    must be wrapped around with :class:`tg.controllers.WSGIAppController`.
    
    """

    error = ErrorController()

    @expose("scriptspony.templates.index")
    def index(self, locker=None, sudo=False, **kwargs):
        """Handle the front-page."""
        if locker is not None and request.response_ext:
            locker += request.response_ext

        olocker = locker
        hosts = None
        pools = None
        user = auth.current_user()
        https = auth.is_https()
        # Find or create the associated user info object.
        # TODO: is there a find_or_create sqlalchemy method?
        if user:
            if sudo and auth.on_scripts_team():
                # override_template(self.index, 'mako:scripts.templates.confirm')
                # return dict(action=url('/new/'+locker),title="Really use Scripts Team bits to request a hostname as locker '%s'?"%locker,question="Only do this in response to a user support request, and after checking to make sure that the request comes from someone authorized to make requests for the locker.",
                #           backurl=url('/index'))
                redirect("/new/%s?confirmed=true" % locker)
            try:
                user_info = (
                    DBSession.query(UserInfo).filter(UserInfo.user == user).one()
                )
            except NoResultFound:
                user_info = UserInfo(user)
                DBSession.add(user_info)
        else:
            user_info = None

        if user is not None:
            if locker is None:
                locker = user
            try:
                hosts = vhosts.list_vhosts(locker)
                hosts.sort(key=lambda k: k[0])
            except auth.AuthError as e:
                flash(e.message)
                # User has been deauthorized from this locker
                if locker in user_info.lockers:
                    user_info.lockers.remove(locker)
                    DBSession.add(user_info)
                if olocker is not None:
                    return self.index()
                else:
                    return dict(hosts={}, locker=locker, user_info=user_info, pools=None)
            else:
                # Append locker to the list in user_info if it's not there
                if not locker in user_info.lockers:
                    user_info.lockers.append(locker)
                    user_info.lockers.sort()
                    DBSession.add(user_info)
                    flash('You can administer the "%s" locker.' % locker)
        if any(host[3] for host in hosts):
            # Only show Pool column if one or more of the vhosts are
            # not on the default pool.
            pools = vhosts.list_pools()
            pools[None] = {'description': 'Default'}
        return dict(hosts=hosts, locker=locker, user_info=user_info, https=https, pools=pools)

    @expose("scriptspony.templates.edit")
    def edit(self, locker, hostname, pool=None, path=None, token=None, alias="", **kwargs):
        if request.response_ext:
            hostname += request.response_ext
        if path is not None or pool is not None:
            if token != auth.token():
                flash("Invalid token!")
            else:
                try:
                    if path is not None:
                        vhosts.set_path(locker, hostname, path)
                    if pool is not None:
                        vhosts.set_pool(locker, hostname, pool)
                except vhosts.UserError as e:
                    flash(e.message)
                else:
                    flash("Host '%s' reconfigured." % hostname)
                    redirect("/index/" + locker)
        else:
            if alias:
                if token != auth.token():
                    flash("Invalid token!")
                else:
                    try:
                        vhosts.add_alias(locker, hostname, alias)
                    except vhosts.UserError as e:
                        flash(e.message)
                    else:
                        flash("Alias '%s' added to hostname '%s'." % (alias, hostname))
                        redirect("/index/" + locker)
        try:
            info = vhosts.get_vhost_info(locker, hostname)
        except vhosts.UserError as e:
            flash(e.message)
            redirect("/index/" + locker)
        pools = vhosts.list_pools()
        pool_choices = []
        pool_choices.append({"name": 'Default', "value": 'DEFAULT', "selected": info['poolIPv4'] is None})
        for ip, pool in pools.items():
            # TODO: Only show selectable pools
            if pool["scriptsVhostPoolUserSelectable"] == "TRUE":
               pool_choices.append({"name": pool["description"], "value": ip, "selected": info['poolIPv4'] == ip})
        if not any(choice["selected"] for choice in pool_choices):
            name = pools.get(info['poolIPv4'], {"description": info['poolIPv4']})["description"]
            pool_choices.insert(0, {"name": "Unchanged (%s)" % (name,), "value": "", "selected": True})
        return dict(
            locker=locker, hostname=hostname, path=info["path"], aliases=info["aliases"], alias=alias, pool_choices=pool_choices,
        )

    @expose("scriptspony.templates.delete")
    def delete(self, locker, hostname, confirm=False, token=None, **kwargs):
        if request.response_ext:
            hostname += request.response_ext
        if confirm:
            if token != auth.token():
                flash("Invalid token!")
            else:
                try:
                    vhosts.delete(locker, hostname)
                except vhosts.UserError as e:
                    flash(e.message)
                else:
                    flash("Host '%s' deleted." % hostname)
                    redirect("/index/" + locker)
        try:
            info = vhosts.get_vhost_info(locker, hostname)
        except vhosts.UserError as e:
            flash(e.message)
            redirect("/index/" + locker)
        return dict(locker=locker, hostname=hostname, path=info["path"], aliases=info["aliases"])

    @expose("scriptspony.templates.new")
    def new(
        self,
        locker,
        hostname="",
        path="",
        desc="",
        token=None,
        confirmed=False,
        personal_ok=False,
        requestor=None,
        **kwargs
    ):
        personal = locker == auth.current_user()
        if confirmed:
            auth.scripts_team_sudo()
        else:
            requestor = None
        if request.response_ext:
            locker += request.response_ext
        if hostname:
            if token != auth.token():
                flash("Invalid token!")
            elif not desc and not confirmed:
                flash("Please specify the purpose of this hostname.")
            elif requestor is not None and not requestor.strip():
                flash("Please specify requestor.")
            elif personal and not personal_ok:
                flash(
                    "Please acknowledge that your hostname will be served from your personal locker and will be deleted when you leave MIT."
                )
            else:
                try:
                    status = vhosts.request_vhost(
                        locker, hostname, path, user=requestor, desc=desc
                    )
                except vhosts.UserError as e:
                    flash(e.message)
                else:
                    flash(status)
                    if confirmed:
                        redirect("/queue")
                    else:
                        redirect("/index/" + locker)
        else:
            try:
                auth.validate_locker(locker, sudo_ok=True)
            except auth.AuthError as e:
                flash(e.message)
                redirect("/")

        return dict(
            locker=locker,
            hostname=hostname,
            path=path,
            desc=desc,
            confirmed=confirmed,
            personal=personal,
        )

    @expose("scriptspony.templates.queue")
    @scripts_team_only
    def queue(self, **kw):
        all = ("open", "moira", "dns", "resolved", "rejected")
        if len(kw) <= 0:
            kw = dict(open="1", moira="1", dns="1")
        query = queue.Ticket.query
        for k in all:
            if k not in kw:
                query = query.filter(queue.Ticket.state != k)
        return dict(tickets=query.all(), all=all, included=kw)

    @expose("scriptspony.templates.ticket")
    @scripts_team_only
    def ticket(self, id, **kwargs):
        return dict(tickets=[queue.Ticket.get(int(id))])

    @expose("scriptspony.templates.message")
    @scripts_team_only
    def approve(self, id, subject=None, body=None, token=None, silent=False, **kwargs):
        t = queue.Ticket.get(int(id))
        if t.state != "open":
            flash("This ticket's not open!")
            redirect("/ticket/%s" % id)
        if t.rtid is None:
            flash("This ticket has no RT ID!")
            redirect("/ticket/%s" % id)
        if subject and body:
            if token != auth.token():
                flash("Invalid token!")
            else:
                try:
                    vhosts.actually_create_vhost(t.locker, t.hostname, t.path)
                except vhosts.UserError as e:
                    flash(e.message)
                else:
                    if not silent:
                        # Send mail and records it as an event
                        rt.call(
                            "ticket/%d/comment" % (t.rtid,),
                            Action="comment",
                            Text=body,
                            Cc="accounts-internal@mit.edu",
                        )

                        t.addEvent(
                            type="mail",
                            state="moira",
                            target="accounts-internal",
                            subject=subject,
                            body=body,
                        )
                        flash("Ticket approved; mail sent to accounts-internal.")
                    else:
                        rt.call(
                            "ticket/%d/comment" % (t.rtid,),
                            Action="comment",
                            Text="Ticket approved silently.\n\n" + body,
                        )
                        t.addEvent(type="mail", state="dns", target="us")
                        flash("Ticket approved silently.")
                    redirect("/queue")
        short = t.hostname[: -len(".mit.edu")]
        assert t.hostname[0] != "-"
        stella = subprocess.Popen(
            ["/usr/bin/stella", t.hostname],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = stella.communicate()
        return dict(
            tickets=[t],
            action=url("/approve/%s" % id),
            subject="scripts-vhosts CNAME request: %s" % short,
            body="""Hi accounts-internal,

At your convenience, please make %(short)s an alias of scripts-vhosts.

stella scripts-vhosts -a %(short)s

Thanks!
-%(first)s
SIPB Scripts Team

/set status=stalled
"""
            % dict(short=short, first=auth.first_name()),
            help_text_html="<p>Make sure the host name is not being used:</p><pre>$ stella %s\n%s\n%s</pre><p>If it's DELETED, you need to forward explicit confirmation that it's OK to reuse (from owner/contact/billing contact, or rccsuper for dorms, or a FSILG's net contact, or similar).</p>"
            % (cgi.escape(t.hostname), cgi.escape(out), cgi.escape(err)),
            extra_buttons={"silent": "Approve without mailing accounts-internal"},
        )

    @expose("scriptspony.templates.message")
    @scripts_team_only
    def reject(self, id, subject=None, body=None, token=None, silent=False, **kwargs):
        t = queue.Ticket.get(int(id))
        if t.state != "open":
            flash("This ticket's not open!")
            redirect("/ticket/%s" % id)
        if t.rtid is None:
            flash("This ticket has no RT ID!")
            redirect("/ticket/%s" % id)
        if (subject and body) or silent:
            if token != auth.token():
                flash("Invalid token!")
            else:
                # Send mail and records it as an event
                if not silent:
                    rt.call(
                        "ticket/%d/comment" % (t.rtid,), Action="correspond", Text=body
                    )
                    t.addEvent(
                        type=u"mail",
                        state=u"rejected",
                        target=u"user",
                        subject=subject,
                        body=body,
                    )
                    flash("Ticket rejected; mail sent to user.")
                else:
                    rt.call(
                        "ticket/%d/comment" % (t.rtid,),
                        Action="comment",
                        Text="Ticket rejected silently.\n\n" + body,
                    )
                    t.addEvent(
                        type=u"mail",
                        state=u"rejected",
                        target=u"rt",
                        subject=subject,
                        body=body,
                    )
                    flash("Ticket rejected silently.")
                redirect("/queue")
        return dict(
            tickets=[t],
            action=url("/reject/%s" % id),
            subject="Re: Request for hostname %s" % t.hostname,
            body="""Hello,

Unfortunately, the hostname %(hostname)s is not available.  You can go to https://pony.scripts.mit.edu/ to request a different one.

Sorry for the inconvenience,
-%(first)s

/set status=rejected
"""
            % dict(hostname=t.hostname, first=auth.first_name()),
            submit="Send to %s" % t.requestor,
            extra_buttons={"silent": "Send as Comment"},
        )
