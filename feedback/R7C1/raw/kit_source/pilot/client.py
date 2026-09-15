"""Shared transport exceptions; no legacy experiment entry points."""
import urllib.request

class RunStopped(RuntimeError): pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl): return None
