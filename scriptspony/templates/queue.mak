<%inherit file="scriptspony.templates.master"/>

<table border="1">
  <tr><th></th><th>Requestor</th><th>Locker</th><th>Hostname</th><th>Path</th><th>State</th></tr>
  %for t in tickets:
    <tr><td><a href="${tg.url('/ticket/%s'%t.id)}">${t.id}</a></td><td>${t.requestor}</td><td>${t.locker}</td><td>${t.hostname}</td><td>${t.path}</td><td>${t.state}</td></tr>
  %endfor
</table>
