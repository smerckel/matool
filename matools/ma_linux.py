"""
Part of matool.

Licensed under GPL, see the file ../COPYRIGHT

Lucas Merckelbach lucas.merckelbach@hzg.de
31 May 2011, Gulf of Biscay
"""
import os
import sys
import subprocess
from time import sleep

ConfigPath = os.path.join(os.environ['HOME'],'.config', 'matools', 'matoolrc')
User = os.environ['USER']
DefaultEditor = "/usr/bin/gedit"

class TunnelAgent(object):
    def __init__(self,host,user,port_local,
                 ma_server,ma_server_port,gracetime):
        self.host=host
        self.port_local=port_local
        self.ma_server=ma_server
        self.ma_server_port=ma_server_port
        self.gracetime=gracetime
        self.password=None
        self.user=user
        self.cmd="ssh -f -L %d:%s:%d %s@%s sleep %d"%(port_local,
                                                      ma_server,
                                                      ma_server_port,
                                                      user,
                                                      host,
                                                      gracetime)
        
    def connect(self):
        p = subprocess.Popen(self.cmd,shell=True)
        rt=p.wait()
        sys.stdout.write("Using ssh command : {}\n".format(self.cmd))
        if rt==0:
            sys.stdout.write("Opened ssh tunnel.\n")
        else:
            sys.stderr.write("Ssh command failed.\n")
            sys.stderr.write("Used command : %s.\n"%(self.cmd))
            
