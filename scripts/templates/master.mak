<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<%!
import pylons
from socket import gethostname
from scripts import auth, log
import os
from datetime import datetime

scriptshost = gethostname()

def set_port(url,port):
    if port == 80:
        portbit = ""
        newprot = 'http'
    else:
        portbit = ":%d"%port
        newprot = 'https'
    prot,rest = url.split('://',1)
    if '/' in rest:
        host,rester = rest.split('/',1)
    else:
        host = rest
        rester = ''
    if ':' in host:
        host = host.split(':')[0] + portbit
    else:
        host += portbit
    return newprot+"://"+host+"/"+rester

if log.unusual_locker():
   lockertag = '[%s] ' % log.get_tag()
else:
   lockertag = ''

%>

<%def name="head()">
    <%
    pink = request.cookies.get('pink',auth.current_user() in ('geofft','mitchb'))
    %>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="Content-Style-Type" content="text/css" />
    %if pink:
      <link rel="stylesheet" href="${tg.url('/scripts/ponies.css')}" type="text/css" />
    %else:
      <link rel="stylesheet" href="${tg.url('/scripts/style.css')}" type="text/css" />
    %endif
    <link rel="stylesheet" href="${tg.url('/scripts/server.css')}" type="text/css" />
    <style type="text/css">
      table {width: 100%; margin-bottom: 10px}
      textarea {width: 100%; height: 250px}
      input[type=text] {width: 200px}
      input[type=text].wide {width: 400px}
      small {color:grey}
    </style>
    <title>${lockertag}${self.title()}</title>
    <script type="text/javascript"><!--
      var kkeys = [], konami = "38,38,40,40,37,39,37,39,66,65";
      document.onkeydown = function (e) {
        kkeys.push(e.keyCode);
        var idx = kkeys.toString().indexOf( konami );
        if (idx >= 0 && idx != kkeys.toString().length - konami.length) {
          kkeys = [];
          rainbow();
        }
      };
      function rainbow () {
%if pink:
        document.cookie = "pink=";
%else:
        document.cookie = "pink=yay";
%endif
        window.location.reload()
      }
    //--></script>
</%def>

<head>
  ${self.head()}
</head>

<body>
<div id="farouter">
	<div id="outer">
			<div id="masthead">

				<h1 id="header"><a rel="home" href="${tg.url('/')}">${lockertag}${self.title()}</a></h1>
				<h2 id="tagline">${self.tagline()}</h2>
			</div>
			<div id="hmenu">
				<div id="hnav">
				  <ul id="navlist"><li id="pageLogin">
      %if not auth.current_user():
        <a href="${set_port(pylons.request.application_url,444)}">Login with MIT Certificates</a>
      %else:
        Welcome ${auth.first_name()}.
        <a href="${set_port(pylons.request.application_url,80)}">Logout</a>
      %endif
    </li>
    %if auth.on_scripts_team():
      <li><a href="${tg.url('/queue')}">Admin Queue</a></li>
    %endif    
    <li><a href="http://scripts.mit.edu/">scripts.mit.edu home</a></li>
</ul>

				</div>
			</div>

		<div id="rap">
			<div id="main">
				<div id="content">

<%
tg_flash = tg.flash_obj.render('flash', use_js=False)
%>
%if tg_flash:
  <h4 id="status_block" class="flash">
    ${tg_flash|n}
  </h4> 
%endif

      ${next.body()}

<p>&nbsp;</p>

<center><small>&copy; 2009-${datetime.now().year}, the SIPB scripts.mit.edu project.<br/>These pages may be reused under either the <a href="/nolink/81/">GFDL 1.2</a> or <a rel="license" href="http://creativecommons.org/licenses/by-sa/3.0/us/">CC-BY-SA 3.0</a>.<br/>Questions? Contact <a href="mailto:scripts@mit.edu">scripts@mit.edu</a>.<br/><br/>

You are currently connected to ${scriptshost}.</small></center>

				</div>
<div id="menu">
					<div id="nav">

<h2>Contact</h2>
Feel free to contact us with any questions, comments, or suggestions.
<ul><li><a href="mailto:scripts@mit.edu">scripts@mit.edu</a></li>
</ul>

<a class="nobutt" href="http://scripts.mit.edu/faq/45/"><img src="${tg.url('/scripts/media/powered_by-trans.gif')}" alt="powered by scripts.mit.edu"/></a>

					</div>
<center><a href="${tg.url('/pony')}" style="color:white">(and ponies)</a></center>
				</div>

		      <div id="clearer">&nbsp;</div>
			</div>
		</div>
		<div id="foot">&nbsp;</div>
	</div>
</div>
</body>
</html>
