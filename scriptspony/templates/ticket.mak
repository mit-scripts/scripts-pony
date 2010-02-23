<%inherit file="scriptspony.templates.master"/>

<table border="1">
  <tr><th></th><th>Requestor</th><th>Locker</th><th>Hostname</th><th>Path</th><th>State</th></tr>
  <tr><td>${ticket.id}</td><td>${ticket.requestor}</td><td>${ticket.locker}</td><td>${ticket.hostname}</td><td>${ticket.path}</td><td>${ticket.state}</td></tr>
</table>

<table border="1">
  <tr><th>Time</th><th>Who</th><th>Event</th><th>Target</th></tr>
  %for e in ticket.events:
    <tr><td>${e.timestamp}</td><td>${e.by}</td><td>${e.type}</td><td>${e.target}</td></tr>
    %if e.subject:
       <tr><td></td><td colspan="3">${e.subject}</td></tr>
    %endif
    %if e.body:
       <tr><td></td><td colspan="3">${e.body}</td></tr>
    %endif
  %endfor
</table>
