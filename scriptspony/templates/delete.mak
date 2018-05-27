<%inherit file="scripts.templates.master"/>

<%!
from scripts.auth import token
%>

<div><a href="${tg.url('/')}">&laquo; Back to list</a></div>

<form method="post">
  <ul>
    <li>Hostname: ${hostname}</li>
    <li>Locker: ${locker}</li>
    <li>Path: /mit/${locker}/web_scripts/${path}</li>
    %if len(aliases) > 0:
      <li>
        Aliases:
        <ul>
          %for a in aliases:
            <li>${a}</li>
          %endfor
        </ul>
      </li>
    %endif
  </ul>

  <p>Are you sure you want to <strong>delete</strong> this hostname?</p>

  <input type="hidden" name="confirm" value="true" />
  <button class="btn btn-danger"><span class="fa fa-times-circle"></span> Yes, delete ${hostname}</button>
  <input type="hidden" name="token" value="${token()}" />
</form>
