<%inherit file="scriptspony.templates.master"/>

<h3>Hostnames for the ${locker} locker</h3>

%if hosts is not None:
  <p>
    <table border="1">
      <tr><th>Hostname</th><th>Path</th></tr>
      %for host,path in hosts:
        <form method="post">
          <tr>
	    <td>${host}</td><td>${path}</td>
	    %if host not in (locker+'.scripts.mit.edu',):
	      <td><a href="${tg.url('edit/'+locker+'/'+host)}">edit</a></td>
	    %endif
          </tr>
	</form>
      %endfor
    </table>
    
    Paths are relative to the services root; for example, 
    <tt>/mit/lockername/web_scripts/</tt> or 
    <tt>/mit/lockername/Scripts/svn/</tt>.
  </p>
  <p>
    <a href="${tg.url('/new/'+locker)}">Request a new hostname</a> for the ${locker} locker
  </p>
  <form action="${tg.url('/index')}">
    Switch to managing the <input type="text" name="locker" value="${locker}" /> locker
    <input type="submit" value="Switch" />
  </form>  
%else:
  <p>Scripts Pony!  This useful tool lets you configure all the
  hostnames you use for scripts.mit.edu websites.  Log in with your MIT
  certificates above.</p>
%endif
