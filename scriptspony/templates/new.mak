<%inherit file="scripts.templates.master"/>

<%!
from socket import gethostbyname
from scripts.auth import token
%>

<div><a href="${tg.url('/index/'+locker)}">Back to list</a></div>

<form method="post">
  %if confirmed:
    <p class="alarming">Warning!  You are using your Scripts Team bits
      to force-submit a request!  Only do this in response to a user request!
      Be careful!</p>
  %endif
  <p>You about to request a hostname for the <b>${locker}</b> locker. If you purchased a domain and want to associate it with Scripts, your request will be automatically approved. <a href="http://scripts.mit.edu/faq/14/do-cnames-work-with-the-script-service">Our FAQ has details on the process</a>.</p>
  <p>Requests for hostnames ending in ".${locker}.scripts.mit.edu" will also be automatically approved.</p>
  <p>If you want a different hostname ending in ".mit.edu", this will require approval by the Scripts team, get forwarded to IS&T for processing, and then become active after a few business days.</p>
  <ul>
    %if confirmed:
      <li>Requestor: <input type="text" name="requestor" value="" /></li>
    %endif
    <li>Hostname: <input type="text" name="hostname" value="${hostname}" /></li>
    <li>Path: /mit/${locker}/web_scripts/<input type="text" name="path" value="${path}" /></li>
    %if not confirmed:
      <li>Purpose: <textarea name="desc">${desc}</textarea></li>
    %endif
  </ul>
  <input type="submit" value="Request Hostname" />
  <input type="hidden" name="token" value="${token()}" />
  %if confirmed:
    <input type="hidden" name="confirmed" value="1" />
  %endif
</form>
