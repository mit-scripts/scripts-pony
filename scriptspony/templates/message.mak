<%inherit file="scriptspony.templates.queue"/>

<%!
from scriptspony import auth
%>

<p>Be sure to check the hostname with stella before sending.  (DNS got
checked on request, but it could still be reserved or there could be a
race going on.)</p>

<form action="${action}" method="post">
  <label>Subject: <input type="text" name="subject" value="${subject}" /></label><br/>
  <label>Body:
    <textarea name="body">${body}</textarea>
  </label>
  <input type="submit" value="Send" />
  <input type="hidden" name="token" value="${auth.token()}" />
</form>
