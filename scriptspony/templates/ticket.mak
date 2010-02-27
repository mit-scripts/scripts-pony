<%inherit file="scriptspony.templates.queue"/>

<table border="1">
  <tr><th>Time</th><th>Who</th><th>Event</th><th>Target</th></tr>
  %for e in tickets[0].events:
    <tr><td>${e.timestamp}</td><td>${e.by}</td><td>${e.type}</td><td>${e.target}</td></tr>
    %if e.subject:
       <tr><td></td><td colspan="3" style="font-size:x-small">${e.subject}</td></tr>
    %endif
    %if e.body:
       <tr><td></td><td colspan="3" style="font-size:xx-small"">${e.body}</td></tr>
    %endif
  %endfor
</table>
