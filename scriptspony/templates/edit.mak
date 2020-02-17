<%inherit file="scripts.templates.master"/>

<%!
from scripts.auth import token
%>

<div><a href="${tg.url('/')}">&laquo; Back to list</a></div>

<form method="post">
  <ul>
    <li>Hostname: ${hostname}</li>
    <li>Locker: ${locker}</li>
    <li>Path: /mit/${locker}/web_scripts/<input type="text" name="path" value="${path}" /></li>
    <li>Server Pool: ${pool} <select name="pool">
    <option value="unchanged">Unchanged</option>
    <option value="default">Default</option>
    %for ip, description in pools.items():
    <option value="${ip}">${description}</option>
    %endfor
    </select></li>
  </ul>
  <button class="btn"><span class="fa fa-save"></span>Save Changes</button>
  %if hostname.lower().endswith('.'+locker+'.scripts.mit.edu') or not hostname.lower().endswith('.mit.edu'):
    <a class="btn btn-danger" href="${tg.url('/delete/'+locker+'/'+hostname)}"><span class="fa fa-times-circle"></span> Delete</a>
  %endif
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
  %if hostname.lower().endswith('.'+locker+'.scripts.mit.edu') or not hostname.lower().endswith('.mit.edu'):
    <form method="post">
      <input type="text" name="alias" value="${alias}" />
      <button class="btn"><span class="fa fa-plus"></span> Add Alias</button>
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
