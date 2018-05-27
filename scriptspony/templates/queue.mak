<%inherit file="scripts.templates.master"/>

<table border="1">
  <tr><th>#</th><th>RT ID</th><th>User</th><th>Locker</th><th>Hostname</th><th>State</th><th colspan="2">Actions</th></tr>
  %for t in tickets:
    <tr>
      <td><a href="${tg.url('/ticket/%s'%t.id)}">${t.id}</a></td>
      %if t.rtid is not None:
        <td><a href="https://help.mit.edu/Ticket/Display.html?id=${t.rtid}">${t.rtid}</a></td>
      %else:
        <td></td>
      %endif
      <td>${t.requestor}</td><td>${t.locker}</td><td>${t.hostname}</td><td>${t.state}</td>
      %if t.state == 'open':
        <td><a href="${tg.url('/approve/%s'%t.id)}" class="btn sm-btn" aria-label="Approve" title="Approve"><span class="fa fa-check" aria-hidden="true"></span></a></td>
        <td><a href="${tg.url('/reject/%s'%t.id)}" class="btn btn-danger sm-btn" aria-label="Reject" title="Reject"><span class="fa fa-ban" aria-hidden="true"></span></a></td>
      %else:
        <td></td><td></td>
      %endif
    </tr>
%if t.state == 'open':
    <tr>
    <td colspan="8"><strong>Purpose:</strong> ${t.purpose}</td>
    </tr>
%endif
  %endfor
</table>

%if next is not UNDEFINED and hasattr(next,'body'):
  ${next.body()}
  <p><a href="${tg.url('/queue')}">Back to queue</a></p>
%else:
  <form method="get">
    Display tickets that are:
    %for s in all:
      <label><input type="checkbox" name="${s}" value="1"${' checked' if s in included else ''} /> ${s}</label>
    %endfor
    <button class="btn"><span class="fa fa-filter"></span> Filter</button>
  </form>
%endif
