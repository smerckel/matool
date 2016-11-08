''' ma_edit: module for interacting with ma_edit_server

    Provides:
	class Editor
	class Ma_Edit_Client   : to edit files on the dockserver
	class Ma_Status_Client : to queary the ma_edit_server

Licensed under GPL, see the file ../COPYRIGHT

Lucas Merckelbach lucas.merckelbach@hzg.de
31 May 2011, Gulf of Biscay
	
 '''

from . import xmlprotocol
import sys
from socket import *
import os
import subprocess
import tempfile
from functools import reduce

REQUIRED_VERSION='0.50' # client requires this server version.

class Editor(object):
    def __init__(self,editor='/usr/bin/emacs'):
        self.editor=editor
    
    def open(self,fn):
        #R = subprocess.check_call([self.editor,fn])
        #return R
        p = subprocess.Popen([self.editor,fn],shell=False,stderr=subprocess.PIPE)
        p.wait()
        return p.returncode

class Client(object):
    ''' a simple tcp client'''
    def __init__(self,host,port,bufferlength=1024):
        self.host=host
        self.port=port
        self.bufferlength=bufferlength

    def init(self):
        self.s=socket(AF_INET,SOCK_STREAM)

    def __connect(self):
        try:
            self.s.connect((self.host,self.port))
        except error:
            sys.stderr.write("Could not connect to ma_edit_server (%s:%d).\n"%(self.host,self.port))
            raise error
        hellob = self.s.recv(16)
        hello=hellob.decode('utf-8').rstrip()
        if not hello:
            msg="Could not connect to ma_edit_server (%s:%d).\n"%(self.host,self.port)
            msg+="Perhaps it is not running?\n"
            raise ValueError(msg)
        Id,version=hello.split("V")
        return Id,version

    def connect(self):
        self.init()
        self.__connect()

    def write(self,mesg):
        mesgb=bytes(mesg,encoding='utf-8')
        self.s.send(mesgb)

    def read(self):
        datab=self.s.recv(self.bufferlength)
        data=datab.decode('utf-8')
        if data:
            while True:
                if data.endswith('</packet>'):
                    break
                datab=self.s.recv(self.bufferlength)
                data+=datab.decode('ascii')
        return data

    def readlines(self):
        lines=[]
        while True:
            line=self.read()
            if line=="": break
            lines.append(line)
        allLines="".join(lines)
        return allLines

    def close(self):
        self.s.close()
        
    def checkServerStatus(self):
        self.init()
        self.s.settimeout(5)
        try:
            ID,version=self.__connect()
            R=(ID==xmlprotocol.ID,version,REQUIRED_VERSION)
            self.close()
        except timeout:
            R=(False,0,0)
        except error:
            R=(False,0,0)
        return R

    def anyfile(self,glider,filename):
        self.status()
        self.connect()
        request=xmlprotocol.AnyFile(glider,filename)
        msg = request()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        content = r.packet.getElementsByTagName('content')[0]
        t = "".join([i.nodeValue for i in content.childNodes])
        return t

    def status(self):
        self.queue={}
        self.connect()
        requestStatus=xmlprotocol.QueueStatus()
        msg = requestStatus()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        if r.type=='response' and r.action=='queuestatus':
            for s in r.childrenByName('qentry'):
                self.queue[(s['glider'],s['filename'])]=s['author']
        return xmlprotocol.OK

class Ma_Edit_Client(Client):
    def __init__(self,glider,filename,revision,user,
                 host='localhost',port=9000):
        Client.__init__(self,host,port)
        self.glider = glider
        self.filename = filename
        self.revision = revision
        self.user = user
        self.ticket=None
        self.xml_sendfile=xmlprotocol.SendMafile(glider,filename,user)
        self.xml_returnfile=xmlprotocol.ReturnMafile()

    def requestFile(self):
        msg = self.xml_sendfile()
        self.write(msg)
        answer=self.readlines()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        content = r.packet.getElementsByTagName('content')[0]
        t = "".join([i.nodeValue for i in content.childNodes])
        d = dict((k,v) for k,v in r.children['content'])
        return d['ticket'],t,d['revision']

    def isContentModified(self,fn,content):
        fd = open(fn,'r')
        contentNew="".join(fd.readlines())
        fd.close()
        same=len(content)==len(contentNew)
        if same:
            for i,j in zip(content,contentNew):
                if i!=j:
                    same=False
        return not same

    def askToContinue(self,txt):
        ans = input(txt)
        while not ans in ['y','Y','n','N']:
            ans = input(txt)
        return ans in ['y','Y']

    def invokeEditor(self,content,editor):
        if self.filename.endswith("ma"):
            suffix=".ma"
        elif self.filename.endswith("mi"):
            suffix=".mi"
        else:
            suffix=""
        ifd,tmpname=tempfile.mkstemp(suffix=suffix)
        fd=os.fdopen(ifd,'w')
        fd.write(content)
        fd.close()
        editor=Editor(editor=editor)
        R=editor.open(tmpname)
        if sys.platform.startswith('linux'):
            if R!=0:
                raise ValueError('External editor did not finish properly.')
            if self.isContentModified(tmpname,content):
                a=self.askToContinue("Propagate modifications? (y/n) ")
            else:
                a=self.askToContinue("File was not modified. Continue? (y/n) ")
        else:
            # on windows platform notepad doesn't wait for the editing to be finised.
            a=self.askToContinue("When finished editing (i.e. editor is closed), progagate changes (if any)? (y/n) ")
        return a,tmpname

    def returnFile(self,ticket,tmpfn):
        fd = open(tmpfn,'r')
        content = "".join(fd.readlines())
        fd.close()
        self.xml_returnfile.add_content(ticket,content)
        msg = self.xml_returnfile()
        self.write(msg)
        answer=self.readlines()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        content = r.packet.getElementsByTagName('result')[0]
        d = dict((k,v) for k,v in r.children['result'])
        return int(d['accept'])

    def pre_edit(self,content):
        if self.revision:
            # overwrite content.
            content=self.anyfile(self.glider,self.filename+".%03d"%(int(self.revision)))
        return content

    def edit(self,editor):
        self.connect()
        ticket,content,revision =self.requestFile()
        self.close()
        content=self.pre_edit(content)
        a,tmpfn = self.invokeEditor(content,editor)
        r=xmlprotocol.ABORT
        if a:
            self.connect()
            r=self.returnFile(ticket,tmpfn)
            self.close()
        os.remove(tmpfn)
        return r,revision

class Ma_Edit_Log_Client(Ma_Edit_Client):
    """ Class to edit log files. Subclasses from ma_edit_client 
        and redefines a number of methods.
    """
    def __init__(self,glider,user,
                 host='localhost',port=9000,client_options=[""]):
        filename="log"
        self.initial_text=client_options[0]
        self.optional_info=client_options[1]
        Ma_Edit_Client.__init__(self,glider,filename,None,user,host,port)
        self.xml_sendfile=xmlprotocol.SendLogfile(glider,user)
        self.xml_returnfile=xmlprotocol.ReturnLogfile()

    def pre_edit(self,content):
        s="%s\n\n\n\n%s\n%s%s\n"%(self.initial_text,
          "============ this line and everything below it will be ignored ===============",
          self.optional_info,                     
          "   Reverse log entries for %s."%(self.glider.upper()))
        content=self.reverse_log_file(content)
        content=s+content
        return content

    def reverse_log_file(self,logtext):
        blocks=[]
        MARK="---------- MARK ----------"
        block=[MARK]
        for i in logtext.split("\n"):
            if i==MARK:
                blocks.append(block)
                block=[i]
                continue
            block.append(i)
        blocks.append(block)
        blocks.reverse()
        txt=reduce(lambda x,y:x+y,blocks,[""])
        return "\n".join(txt)
        
class Ma_Edit_Import(Client):
    def __init__(self,glider,user,
                 host='localhost',port=9000):
        Client.__init__(self,host,port)
        self.glider = glider
        self.user = user
        self.ticket=None
        

    def requestFile(self,filename):
        sendmafile=xmlprotocol.SendMafile(self.glider,filename,self.user)
        msg = sendmafile()
        self.write(msg)
        answer=self.readlines()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        content = r.packet.getElementsByTagName('content')[0]
        t = "".join([i.nodeValue for i in content.childNodes])
        d = dict((k,v) for k,v in r.children['content'])
        return d['ticket'],t,d['revision']

    def askToContinue(self,txt):
        ans = input(txt)
        while not ans in ['y','Y','n','N']:
            ans = input(txt)
        return ans in ['y','Y']


    def returnFile(self,ticket,tmpfn):
        try:
            fd = open(tmpfn,'r')
        except FileNotFoundError:
            return 0
        else:
            content = "".join(fd.readlines())
            fd.close()
        returnmafile=xmlprotocol.ReturnMafile()
        returnmafile.add_content(ticket,content)
        msg = returnmafile()
        self.write(msg)
        answer=self.readlines()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        content = r.packet.getElementsByTagName('result')[0]
        d = dict((k,v) for k,v in r.children['result'])
        return int(d['accept'])
    
    def upload(self,filename):
        base_filename=os.path.basename(filename)
        self.connect()
        tcr=self.requestFile(base_filename)
        ticket,content,revision = tcr
        self.close()
        r=xmlprotocol.ABORT
        self.connect()
        r=self.returnFile(ticket,filename)
        self.close()
        return r


class Ma_Status_Client(Client):
    def __init__(self,host='localhost',port=9000):
        Client.__init__(self,host,port)
        self.queue={}

    def sendDelete(self,glider,filename):
        self.connect()
        requestDelete=xmlprotocol.Delete(glider,filename)
        msg = requestDelete()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        if r.type=='response' and r.action=='delete':
            d = dict((k,v) for k,v in r.children['result'])
        return int(d['result'])

    def delete(self,glider,filename):
        self.status()
        if (glider,filename) in self.queue:
            errorCode=self.sendDelete(glider,filename)
        else:
            errorCode=xmlprotocol.DELETENOTINQUEUE
        return errorCode

    def current(self,glider,filename):
        self.status()
        self.connect()
        requestCurrent=xmlprotocol.Current(glider,filename)
        msg = requestCurrent()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        content = r.packet.getElementsByTagName('content')[0]
        t = "".join([i.nodeValue for i in content.childNodes])
        return t

    def rereadStatus(self,glider,since=12):
        self.connect()
        request=xmlprotocol.Reread(glider,since)
        msg = request()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        s=r.childrenByName('rereadstatus')
        reread=False
        for sp in s:
            if 'rereadstatus' in sp:
                reread=bool(int(sp['rereadstatus']))
        return reread

    def pickupStatus(self,glider,timestamp="now"):
        self.connect()
        request=xmlprotocol.Pickup(glider,timestamp)
        msg = request()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        s=r.childrenByName('pickupstatus')
        pickup=False
        for sp in s:
            if 'pickupstatus' in sp:
                pickup=bool(int(sp['pickupstatus']))
        return pickup
        
    def lastPositions(self,glider,window=12):
        self.connect()
        requestPosition=xmlprotocol.Position(glider,window)
        msg = requestPosition()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        tm=[]
        lat=[]
        lon=[]
        s=r.childrenByName('position')
        for sp in s:
            if 'time' in sp:
                tm.append(float(sp['time']))
                lat.append(float(sp['latitude']))
                lon.append(float(sp['longitude']))
        x=[(i,j,k) for i,j,k in zip(tm,lat,lon)]
        x.sort()
        s=r.childrenByName('last_waypoint')
        if s:
            x_last_wpt_lat=float(s[0]['last_latitude'])
            x_last_wpt_lon=float(s[0]['last_longitude'])
        else:
            x_last_wpt_lat=None
            x_last_wpt_lon=None
        s=r.childrenByName('waypoint')
        if s:
            c_wpt_lat=float(s[0]['latitude'])
            c_wpt_lon=float(s[0]['longitude'])
        else:
            c_wpt_lat=None
            c_wpt_lon=None

        return x,(x_last_wpt_lat,x_last_wpt_lon),(c_wpt_lat,c_wpt_lon)

    def fileList(self,glider,timestamp=None):
        self.connect()
        requestFilelist=xmlprotocol.FileList(glider,timestamp)
        msg = requestFilelist()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        s=r.childrenByName('file')
        fn=[]
        rev={}
        for t in s:
            if 'name' in t:
                name=t['name']
                fn.append(name)
            if 'revision' in t:
                rev[name]=t['revision']
            else:
                rev[name]=None # should not occur.
        return fn,rev

    def gliderList(self):
        self.connect()
        requestlist=xmlprotocol.GliderList()
        msg = requestlist()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        s=r.childrenByName('glider')
        g=[]
        for t in s:
            if 'name' in t:
                name=t['name']
                g.append(name)
        return g


    def get_xmlscripts(self):
        self.connect()
        requestlist=xmlprotocol.XMLList()
        msg = requestlist()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        s=r.childrenByName('script')
        g=dict(user_scripts=[],factory_scripts=[])
        for t in s:
            if 'name' in t:
                name=t['name']
                tp=t['type']
                g[tp].append(name)
        # sort the scripts
        for k in g.keys():
            g[k].sort()
        return g


class Ma_XML_Client(Client):
    def __init__(self,host='localhost',port=9000):
        Client.__init__(self,host,port)

    def show(self,glider):
        self.connect()
        request=xmlprotocol.XMLScript('show',glider)
        msg = request()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        sn=r.packetAttributes['script_name']
        st=r.packetAttributes['script_type']
        if sn=="":
            s="No script is running."
        else:
            s="Current active script for %s is %s/%s."%(glider,st,sn)
        return s

    def stop(self,glider):
        self.connect()
        request=xmlprotocol.XMLScript('stop',glider)
        msg = request()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        g=r.packetAttributes['return_code']
        s="Stopping script for %s: %s"%(glider,g)
        return g

    def pause(self,glider):
        pass

    def start(self,glider,filename):
        self.connect()
        request=xmlprotocol.XMLScript('start',glider,filename,
                                      script_type="user")
        msg = request()
        self.write(msg)
        answer=self.readlines()
        self.close()
        r = xmlprotocol.XMLReader()
        r.digest(answer)
        g=r.packetAttributes['return_code']
        s="Starting script %s for %s: %s"%(filename,glider,g)
        return g
        

if __name__=='__main__':        
    if 0:
        c = Ma_Edit_Client('mozart','helgo.mi','lucas','141.4.0.159',9000)        
        if c.checkServerStatus():
            r=c.edit()
            msg = [xmlprotocol.ERRORMESG[2**i] for i in range(4) if 2**i&r]
            print(msg)  
    if 1:
        s = Ma_Status_Client('localhost',9000)
        if s.checkServerStatus():
            r=s.status()
            pos = s.lastPositions('mozart')
            #pos = s.fileList('amadeus')

#r = s.delete('amadeus','yo50.ma')
