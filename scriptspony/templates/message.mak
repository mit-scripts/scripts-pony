<%inherit file="scriptspony.templates.queue"/>

<form action="${action}" method="post">
  <label>Subject: <input type="text" name="subject" value="${subject}" /></label><br/>
  <label>Body:
    <textarea name="body">${body}</textarea>
  </label>
  <input type="submit" value="Send" />
</form>
