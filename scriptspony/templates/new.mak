<%inherit file="scripts.templates.master"/>

<%!
from socket import gethostbyname
from scripts.auth import token
%>

<div><a href="${tg.url('/index/'+locker)}">Back to list</a></div>

<form method="post">
  %if confirmed:
    <p class="alarming">Warning!  You are using your Scripts Team bits
      to force-submit a request!  Be careful!</p>
  %endif
  <p>
  <ul>
    <li>Locker: ${locker}</li>
    <li>Hostname: <input type="text" name="hostname" value="${hostname}" /></li>
    <li>Path: /mit/${locker}/web_scripts/<input type="text" name="path" value="${path}" /></li>
    <li>Purpose: <textarea name="desc">${desc}</textarea></li>
  </ul>
  <input type="submit" value="Request Hostname" />
  <input type="hidden" name="token" value="${token()}" />
  %if confirmed:
    <input type="hidden" name="confirmed" value="1" />
  %endif
</form>

<p>
  Notes:
  <ul>
    <li>
      You can request any hostname ending with ".${locker}.scripts.mit.edu"
      freely.
    </li>
    <li>Only some hostnames ending with ".mit.edu" are available, and they
      take a few business days to become active.  You can check whether
      a given mit.edu hostname is available by typing "stella &lt;hostname&gt;"
      from an Athena prompt.</li>
    <li>You can request a non-MIT hostname, but you'll have to
      register the hostname yourself and configure it's DNS with a CNAME
      record for "scripts-vhosts.mit.edu." or an A record for
      scripts-vhosts.mit.edu's IP address,
      ${gethostbyname('scripts-vhosts.mit.edu')}.</li>
  </ul>
</p>
