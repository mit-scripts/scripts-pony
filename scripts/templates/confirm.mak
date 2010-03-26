<%inherit file="scripts.templates.master"/>

<%!
from scripts.auth import token
%>

<h1 class="alarming">${title}</h1>

<p class="alarming">${question}</p>

<form action="${action}" method="post">

  <p><label><input type="checkbox" name="confirmed" value="1"
                   />&nbsp;Yes, I'm sure I want to do this.</label></p>

  %if params is not UNDEFINED:
    %for k in params:
      <input name="${k}" value="${params[k]}" type="hidden" />
    %endfor
  %endif
  <input type="hidden" name="token" value="${token()}" />

  <input type="submit" value="Confirm Action" /> <a href="${backurl}">Actually, never mind</a>
</form>
