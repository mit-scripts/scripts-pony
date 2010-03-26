<%inherit file="scripts.templates.master"/>

<%def name="title()">A ${code} Error has Occurred</%def>

<div>${message|n}</div>

<p><a href="${tg.url('/')}">Back to top</a></p>
