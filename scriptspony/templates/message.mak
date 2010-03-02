<%inherit file="scriptspony.templates.queue"/>

<%!
from scriptspony import auth
%>

<form action="${action}" method="post">
  <label>Subject: <input type="text" name="subject" value="${subject}" /></label><br/>
  <label>Body:
    <textarea name="body">${body}</textarea>
  </label>
  <input type="submit" value="Send" />
  <input type="hidden" name="token" value="${auth.token()}" />
</form>
