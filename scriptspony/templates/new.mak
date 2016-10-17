<%inherit file="scripts.templates.master"/>

<%!
from socket import gethostbyname
from scripts.auth import token
%>

<div><a href="${tg.url('/index/'+locker)}">&laquo; Back to list</a></div>

<form method="post">
  %if confirmed:
    <p class="alarming">Warning!  You are using your Scripts Team bits
      to force-submit a request!  Only do this in response to a user request!
      Be careful!</p>
  %endif
  <p>You about to request a hostname for the <b>${locker}</b> locker. If you purchased a domain and want to associate it with Scripts, your request will be automatically approved. <a href="http://scripts.mit.edu/faq/14/do-cnames-work-with-the-script-service">Our FAQ has details on the process</a>.</p>
  <p>Requests for hostnames ending in ".${locker}.scripts.mit.edu" will also be automatically approved.</p>
  <p>If you want a different hostname ending in ".mit.edu", this will require approval by the Scripts team, get forwarded to IS&T for processing, and then become active after a few business days.</p>
  <ul class="form">
    %if confirmed:
    <li><b>Requestor</b>: <input type="text" name="requestor" value=""/></li>
    %endif
    <li><b>Hostname</b>: <input type="text" name="hostname" value="${hostname}" placeholder="hello.${locker}.scripts.mit.edu" /></li>
    <li><b>Path</b>: /mit/${locker}/web_scripts/<input type="text" name="path" value="${path}" /></li>
    %if not confirmed:
      <li><b>Purpose</b>: <textarea name="desc" placeholder="I want this hostname for my student group / course / annual event / pony.">${desc}</textarea></li>
    %endif
  </ul>
  <button class="btn"><span class="fa fa-plus"></span> Request Hostname</button>
  <input type="hidden" name="token" value="${token()}" />
  %if confirmed:
    <input type="hidden" name="confirmed" value="1" />
  %endif
</form>
