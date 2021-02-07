#!/usr/bin/python3

''' ma_server: the server component of matool.


This is a STRIPPED DOWN version of the original ma_edit_server. This program
only looks at the gliders/xxx/archive/ directory to get the latest version of the
file requested, and returns it.

gliderdirectory: this is the path to the glider directory as used by the 
dockserver

logfile: where some comments are dumped for debugging.

This is configured in the file ~/.ma_serverrc and can look like

[Paths]
gliderdirectory=/home/localuser/gliders
logfile=/home/lucas/ma_edit_server.log

[Network]
port=9000


Licensed under GPL, see the file COPYRIGHT

lucas.merckelbach@hzg.de, 1 June 2011

'''
from matools import xmlprotocol
from matools import __version__

from socket import *
import os
import sys
import time
import glob
import configparser


# Modify these three variables to suit your situation:


ConfigFiles=[os.path.join('/usr/local/etc/','ma_serverrc'),
             os.path.join(os.environ['HOME'],'.ma_serverrc')
             ]

Defaults={'gliderdirectory':'gliders',
          'directory':'/var/local/ma_edit_server',
          'repository':'repository',
          'logfile':"ma_server.log"}

Defaults={'gliderdirectory':'/home/lucas/even/ifm',
          'directory':'ma_server',
          'logfile':"ma_server.log"}


class Ma_Edit(object):
    
    def __init__(self):
        config = configparser.ConfigParser(Defaults)
        cnfs=config.read(ConfigFiles)
        print("Reading configuration file(s):")
        for s in cnfs:
            print("\t{}".format(s))

        HD = config.get('Paths','directory')
        try:
            self.checkPath(HD)
        except PermissionError:
            sys.stderr.write("Fatal: Insufficient permissions to modify directory %s.\n"%(HD))
            sys.exit(1)

        if cnfs:
            p = config.get('Paths','gliderdirectory')
            if p.startswith(os.path.sep):
                self.gliderdirectory = p
            else:
                self.gliderdirectory = os.path.join(HD,p)
            p = config.get('Paths','logfile')
            if p.startswith(os.path.sep):
                logfile = p
            else:
                logfile = os.path.join(HD,p)
        else:
            self.gliderdirectory=os.path.join(HD,Defaults['gliderdirectory'])
            logfile=os.path.join(HD,Defaults['logfile'])
            print("Found no configuration file.")
            print("I am going to write one with default settings to %s"%(ConfigFiles[0]))
            print("You may want to edit this file, though.")
            newconfig = configparser.ConfigParser()
            newconfig.add_section('Paths')
            newconfig.set('Paths','gliderdirectory',self.gliderdirectory)
            newconfig.set('Paths','logfile',logfile)
            fp=open(ConfigFile,'w')
            newconfig.write(fp)
            fp.close()

        print("Opening logfile:", logfile)
        self.fd = open(logfile,'a')
        self.cache = {}
        self.queue = {}
        self.configuration=config
        config_summary=dict(cf = cnfs,
                            gdir = self.gliderdirectory,
                            log = logfile)
                            
        self.print_config(config_summary)

    def print_config(self, config_summary):
        print("Configuration summary:")
        print("----------------------")
        print()
        print("Config file     :", config_summary["cf"])
        print()
              
        print("Glider directory:", config_summary['gdir'])
        print("Log file        :", config_summary['log'])
        

    def checkPath(self,path, create_if_not_exists=True):
        if not os.path.exists(path):
            if create_if_not_exists:
                os.makedirs(path)
            return False
        else:
            return True


    def get_ticket(self):
        return "%ld"%(int(time.time()*1000))

    def addToCache(self,ticket,v):
        self.cache[ticket]=v
    
    def retrieveFile(self,glider,filename):
        # MODIFIED wrt ma_edit_server.
        p = os.path.join(self.gliderdirectory,glider,'archive', '*_{}'.format(filename))
        fns = glob.glob(p)
        fns.sort()
        if fns:
            fn = fns[-1]
            fd = open(fn,'r')
            lines=fd.readlines()
            fd.close()
        else:
            lines=[]
        content = "".join(lines)
        return filename, content


class Server(Ma_Edit):
    def __init__(self,port=9000):
        Ma_Edit.__init__(self)
        try:
            port=self.configuration.getint('Network','port')
        except:
            pass
        self.s = socket(AF_INET,SOCK_STREAM)
        self.s.setsockopt(SOL_SOCKET, SO_REUSEADDR,1)
        self.s.bind(('',port))
        self.s.listen(5)
        self.bufferLength=1024
    
    def digest(self,msg):
        r = xmlprotocol.XMLReader()
        r.digest(msg)
        if r.type=='request' and r.action=='queuestatus':
            resp = xmlprotocol.ResponseQueueStatus()
            for (glider,filename),(content,author) in self.queue.items():
                resp.addQueue(glider,filename,author)
            answer = resp.toxml()
        elif r.type=='request' and r.action=='current':
            resp = xmlprotocol.ResponseCurrent()
            d = dict((k,v) for k,v in r.children['mafile'])
            glider=d['glider']
            filename=d['filename']
            fn,content=self.retrieveFile(glider,filename)
            resp.set_content(content)
            answer = resp.toxml()
        else:
            raise ValueError('unknown response')
        return answer, r.type, r.action

    def logger(self, m):
        self.fd.write("{}: {}\n".format(time.ctime(),m))
        self.fd.flush()
        
    def run(self):
        self.logger("Ma_server started.")
        while True:
            client,addr = self.s.accept()
            self.logger("Connection received from {}.".format(addr[0]))
            hello="%sV%-8s"%(xmlprotocol.ID,__version__)
            hellob=bytes(hello,encoding='utf-8')
            client.send(hellob)
            try:
                mesgb = client.recv(self.bufferLength)
            except error as e:
                if e[0]!=104:
                    raise error(e)
                client.close()
                self.logger("Connection from {} closed.".format(addr[0]))
                continue # wait for new connection
            try:
                mesg=mesgb.decode('utf-8')
            except UnicodeDecodeError:
                print("Invalid request from {}. Ignoring.".format(client.getpeername()[0]))
                self.logger("Invalid request from {}. Ignoring.".format(addr[0]))
                client.close()
                self.logger("Connection from {} closed.".format(addr[0]))
                continue
            
            if mesg:
                while True:
                    if mesg.endswith('</packet>'):
                        break
                    mesgb=client.recv(self.bufferLength)
                    mesg+=mesgb.decode('utf-8')
                answer, rtype, raction = self.digest(mesg)
                self.logger("Received {} for {} from {}.".format(rtype, raction, addr[0]))
                answerb=bytes(answer,encoding='utf-8')
                client.send(answerb)
            client.close()
            self.logger("Connection from {} closed.".format(addr[0]))

# main program #

s = Server()
s.run()
        
