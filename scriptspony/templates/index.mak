<%inherit file="scripts.templates.master"/>

<%!
from scripts import auth
%>

%if hosts is not None:
  <h3>Hostnames for the ${locker} locker</h3>

  <p>
    <table border="1">
      <tr><th>Hostname</th><th>Path</th></tr>
      %for host,aliases,path in hosts:
        <tr>
          <td>
	  <a href="http://${host}">${host}</a>
	    %if len(aliases) > 0:
	      <br /><small>(${', '.join(aliases)})</small>
	    %endif
	  </td>
	  <td>
	    <small>/mit/${locker}/web_scripts/</small>${path}
	  </td>
          %if host not in (locker+'.scripts.mit.edu',):
            <td><a href="${tg.url('/edit/'+locker+'/'+host)}">edit</a></td>
          %endif
        </tr>
      %endfor
    </table>
    
    Paths are relative to the top directory for the 
    appropriate service; for example, 
    <tt>/mit/${locker}/web_scripts/</tt> for <a href="http://scripts.mit.edu/web/">web scripts</a> or 
    <tt>/mit/${locker}/Scripts/svn/</tt> for <a href="http://scripts.mit.edu/faq/93/">Subversion</a>.
  </p>
  <p>
    <a href="${tg.url('/new/'+locker)}">Request a new hostname</a> for the ${locker} locker

<hr />
  <p> You can switch to managing a different locker: </p>
  %if len(user_info.lockers) > 1:
    <ul>
    %for l in user_info.lockers:
    <li>
    %if l == locker:
    <b>${l}</b>
    %else:
    <a href="${tg.url('/index', locker=l)}">${l | h}</a>
    %endif
    </li>
    %endfor
    </ul>
  %endif

  </p>
  <form action="${tg.url('/index')}">
   Switch to managing the <input type="text" name="locker" value="${locker}" /> locker
    <input type="submit" value="Switch" />
    %if auth.on_scripts_team():
      <input type="submit" value="Request as Scripts Team" name="sudo" />
    %endif
  </form>
%elif https:
  <p>You don't seem to be presenting a valid certificate.  You may
    wish to consult
    the <a href="http://ist.mit.edu/services/certificates/wizard">IS&amp;T
    Certificate Help Wizard</a>.</p> 
%else:
  <p>
    Welcome to the scripts.mit.edu hostname management tool.  You can
    request short hostnames to refer to your
  <a href="http://scripts.mit.edu/">scripts.mit.edu</a> pages and
  configure the hostnames you already have.  Log in with your MIT
  certificates above.
  </p>
%endif
