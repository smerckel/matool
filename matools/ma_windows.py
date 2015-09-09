"""
Part of matool.

Licensed under GPL, see the file ../COPYRIGHT

Lucas Merckelbach lucas.merckelbach@hzg.de
31 May 2011, Gulf of Biscay
"""
import os

ConfigPath = os.path.join(os.environ['TEMP'],'matool.cnf')
User = os.environ['USERNAME']
DefaultEditor = "C:\windows\system32\write.exe"

class TunnelAgent(object):
    def __init__(self,*p):
        raise ValueError("Setting up tunnels is not implemented under Windows.")
    
