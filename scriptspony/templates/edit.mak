<%inherit file="scriptspony.templates.master"/>

<div><a href="${tg.url('/')}">Back to list</a></div>

<form method="post">
  <ul>
    <li>Hostname: ${hostname}</li>
    <li>Locker: ${locker}</li>
    <li>Path: <input type="text" name="path" value="${path}" /></li>
  </ul>
  <input type="submit" value="Save" />
</form>

