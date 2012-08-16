<%inherit file="scriptspony.templates.queue"/>

<%!
from scripts.auth import token
%>

%if help_text is not UNDEFINED:
  <p>${help_text}</p>
%endif

%if help_text_html is not UNDEFINED:
  ${help_text_html | n}
%endif

<form action="${action}" method="post">
  <label>Subject: <input type="text" name="subject" value="${subject}" class="wide" /></label><br/>
  <label>Body:
    <textarea name="body">${body}</textarea>
  </label>
  <input type="submit" value="${context.get('submit','Send')}" />
  %for n,v in context.get('extra_buttons',{}).items():
    <input type="submit" name="${n}" value="${v}" />
  %endfor
  <input type="hidden" name="token" value="${token()}" />
</form>
