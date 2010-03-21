<%inherit file="scriptspony.templates.master"/>

<%!
from scripts.auth import token
%>

<div><a href="${tg.url('/')}">Back to list</a></div>

<form method="post">
  <ul>
    <li>Hostname: ${hostname}</li>
    <li>Locker: ${locker}</li>
    <li>Path: /mit/${locker}/web_scripts/<input type="text" name="path" value="${path}" /></li>
  </ul>
  <input type="submit" value="Save Path" />
  <input type="hidden" name="token" value="${token()}" />
</form>

<p>
  Aliases:
  <ul>
    %if len(aliases) > 0:
      %for a in aliases:
        <li>${a}</li>
      %endfor
    %else:
      <li>None</li>
    %endif
  </ul>
  %if not hostname.endswith('mit.edu'):
    <form method="post">
      <input type="text" name="alias" value="${alias}" />
      <input type="submit" value="Add Alias" />
      <input type="hidden" name="token" value="${token()}" />
    </form>
  %endif
</p>

<p>
  Notes:
  <ul>
    <li>The path should be a directory containing an <tt>index.html</tt> or
      <tt>index.cgi</tt> file, a webapp, or similar.  The path generally
      shouldn't point at a specific file.</li>
  </ul>
</p>
