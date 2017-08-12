<%inherit file="scripts.templates.master"/>

<%!
from scripts.auth import token


%>

<div><a href="${tg.url('/')}">&laquo; Back to list</a></div>

<h3> The TLS Certificate Process</h3>
<p>
    The process to get a TLS certificate in order to use HTTPS on your scripts domain is currently as follows: 
</p>
<ul>
    <li> You generate a certificate-signing request (CSR) for your host by filling out the form below.</li>
    <li> You get a certificate from a certificate authority (CA) using this CSR.</li>
    <li> Once you have a certificate, paste it below and submit the second form.</li>
</ul>


%if show_only_csr:
<h3> CSR Request Results </h3>

    % if csr_success:
        <p> Your CSR was successfully generated and appears below.</p>
    % else:
        <p> The following error was generated. Please contact us for help.</p>
    % endif
    <pre>${csr_contents}</pre>
%else:

<h3> Request a CSR</h3>
<p>
<form method="post" action="/request_cert/${locker}/${hostname}">
    <input type="checkbox" name="hostname" value="${hostname}" checked="checked" disabled="disabled" id="mainhostname" /><label for="mainhostname">${hostname}</label><br />
    %if not hostname.endswith('mit.edu'):
      %for i,a in enumerate(aliases):
        <input type="checkbox" name="alias${i}" value="${a}" id="alias${i}"><label for="alias${i}">${a}</label><br />
      %endfor
 %endif
  <button class="btn"><span class="fa fa-send"></span> Generate CSR</button>
  <input type="hidden" name="token" value="${token()}" />
</form>
</p>

%endif


<h3> Submit a Certificate</h3>
<i>This step comes after you have requested a cert from a CA using the CSR generated above.</i>
<p>
    Once you have a certificate, you can submit it below. After a certificate is submitted,
    if it is valid, it will take around an hour for the changes to propograte through our system.
</p>
<p>
    If your chain includes multiple certificates to a root CA, please submit them all at once, with
    the end of the chain first.
</p>
<form method="post" id="certform" action="/request_cert/${locker}/${hostname}">
  <textarea name="certificate" rows="20" cols="80" form="certform" placeholder="-----BEGIN CERTIFICATE-----..."></textarea>
  <input type="hidden" name="token" value="${token()}" />
  <button class="btn"><span class="fa fa-handshake-o"></span> Submit certificate</button>
</form>
