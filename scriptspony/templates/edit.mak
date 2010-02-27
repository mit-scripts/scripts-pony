<%inherit file="scriptspony.templates.master"/>

<div><a href="${tg.url('/')}">Back to list</a></div>

<form method="post">
  <ul>
    <li>Hostname: ${hostname}</li>
    <li>Locker: ${locker}</li>
    <li>Path: /mit/${locker}/web_scripts/<input type="text" name="path" value="${path}" /></li>
  </ul>
  <input type="submit" value="Save" />
</form>

<p>
  Notes:
  <ul>
    <li>The path should be a directory containing an <tt>index.html</tt> or
      <tt>index.cgi</tt> file, a webapp, or similar.  The path can't
      point at a specific file.</li>
  </ul>
</p>
