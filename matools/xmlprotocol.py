"""
Part of matool.

Licensed under GPL, see the file COPYRIGHT

Lucas Merckelbach lucas.merckelbach@hzg.de
31 May 2011, Gulf of Biscay
"""

from xml.dom import minidom
from xml.parsers.expat import ExpatError

ID="MA-EDIT"

OK=0
ACCEPT=1
OVERWRITE=2
INVALIDTICKET=4
WRITEERROR=8
DELETESUCCESS=16
DELETEFAILURE=32
DELETENOTFOUND=64
DELETENOTINQUEUE=128
ABORT=256
ERRORMESG={OK:"Success",
           ACCEPT:"File accepted",
           OVERWRITE:"Target file was overwritten",
           INVALIDTICKET:"Mismatch between server and client ticket.",
           WRITEERROR:"Couln't write target file.",
           DELETESUCCESS:"File deleted",
           DELETEFAILURE:"Couldn't delete file",
           DELETENOTFOUND:"File to delete was not found on server",
           DELETENOTINQUEUE:"File to delete is not in the queue of the server",
           ABORT:"Editing cancelled"}


class XMLDoc(minidom.Document):
    def __init__(self):
        minidom.Document.__init__(self)
        packet=self.createElement('packet')
        textNode=self.createTextNode('')
        packet.appendChild(textNode)
        self.appendChild(packet)
        self.packet=packet
    
    def __call__(self):
        return self.toxml()

    def addAttribute(self,element,name,value):
        element.setAttribute(name,value)
    
    def addChild(self,element,child,content=None):
        if content!=None:
            textNode = self.createTextNode(content)
            child.appendChild(textNode)
        element.appendChild(child)
        

class XMLReader:
    ''' base class to read XML packets.
    '''
    def __init__(self):
        self.mesg=None
        self.type=None
        self.action=None
        
    def readPacket(self):
        ''' reads a packet. This should not go wrong. If it does, the
            serial line is closed and others will continue to be
            monitored. If it does go wrong, things have to be investigated
            on per case basis.
        '''
        try:
            doc=minidom.parseString(self.mesg)
        except ExpatError:
            # could not read message. What to do?
            print("failed to read mesg. This is what I got:")
            print("---------------------------")
            print(self.mesg)
            print("---------------------------")
        if not doc.hasChildNodes:
            raise ValueError(" no children. Investigate.")
        # So far so good, the xml message is properly constructed
        # each doc has the form of packet /packet
        packets=doc.getElementsByTagName('packet')
        if len(packets)!=1:
            raise ValueError("some something else than 1 packet in xml doc")
        self.packet=packets[0]
        
    def readPacketAttributes(self):
        self.packetAttributes=dict((i,j) for i,j in list(self.packet.attributes.items()))
    def readPacketChildren(self):
        self.children = dict((k.tagName,list(k.attributes.items())) 
                             for k in self.packet.childNodes)
    def childrenByName(self,name):
        return [dict((k,v) for k,v in list(i.attributes.items()))
                for i in self.packet.getElementsByTagName(name)]

    def digest(self,mesg):
        self.mesg=mesg
        self.readPacket()
        self.readPacketAttributes()
        self.readPacketChildren()
        self.type=self.packetAttributes['type']
        self.action=self.packetAttributes['action']

class SendMafile(XMLDoc):
    ''' requesting for sending an mafile'''
    def __init__(self,glider,mafile,author):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","mafile")
        mafileElement=self.createElement('mafile')
        self.addAttribute(mafileElement,"glider",glider)
        self.addAttribute(mafileElement,"filename",mafile)
        self.addAttribute(mafileElement,"author",author)
        self.addChild(self.packet,mafileElement)


class ResponseMafile(XMLDoc):
    ''' server response and sending an mafile'''
    def __init__(self,mafile,ticket,revision):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","mafile")
        contentElement=self.createElement('content')
        self.addAttribute(contentElement,"ticket",ticket)
        self.addAttribute(contentElement,"revision",revision)
        self.addChild(self.packet,contentElement,mafile)

class SendRemoteMafile(XMLDoc):
    ''' requesting for sending an mafile from server (from-glider directory)'''
    def __init__(self,glider,mafile,author):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","remotemafile")
        mafileElement=self.createElement('mafile')
        self.addAttribute(mafileElement,"glider",glider)
        self.addAttribute(mafileElement,"filename",mafile)
        self.addAttribute(mafileElement,"author",author)
        self.addChild(self.packet,mafileElement)


class ResponseRemoteMafile(XMLDoc):
    ''' server response and sending a remote mafile from-glider directory'''
    def __init__(self,mafile,ticket,revision):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","remotemafile")
        contentElement=self.createElement('content')
        self.addAttribute(contentElement,"ticket",ticket)
        self.addAttribute(contentElement,"revision",revision)
        self.addChild(self.packet,contentElement,mafile)

        
class ReturnMafile(XMLDoc):
    ''' request for accepting a modified mafile'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","returnmafile")

    def add_content(self,ticket,content):
        contentElement=self.createElement('content')
        self.addAttribute(contentElement,"ticket",ticket)
        self.addChild(self.packet,contentElement,content)

class ResponseReturnMafile(XMLDoc):
    ''' server response accepting a modified mafile'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","returnmafile")
        resultElement=self.createElement('result')
        self.addChild(self.packet,resultElement)
    
    def set_results(self,accept):
        resultElement=self.packet.getElementsByTagName('result')[0]
        resultElement.setAttribute('accept',"%d"%(accept))

class QueueStatus(XMLDoc):
    ''' requesting for status of the queue'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","queuestatus")

class ResponseQueueStatus(XMLDoc):
    ''' server response with status of the queue'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","queuestatus")

    def addQueue(self,glider,filename,author):
        QElement=self.createElement('qentry')
        self.addAttribute(QElement,"glider",glider)
        self.addAttribute(QElement,"filename",filename)
        self.addAttribute(QElement,"author",author)
        self.addChild(self.packet,QElement,None)
        
class Delete(XMLDoc):
    ''' requesting for deleting mafile'''
    def __init__(self,glider,mafile):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","delete")
        mafileElement=self.createElement('mafile')
        self.addAttribute(mafileElement,"glider",glider)
        self.addAttribute(mafileElement,"filename",mafile)
        self.addChild(self.packet,mafileElement)
        
class ResponseDelete(XMLDoc):
    ''' server response of delete request'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","delete")
        resultElement=self.createElement('result')
        self.addChild(self.packet,resultElement)
    
    def set_results(self,glider,filename,result):
        resultElement=self.packet.getElementsByTagName('result')[0]
        resultElement.setAttribute('glider',glider)
        resultElement.setAttribute('filename',filename)
        resultElement.setAttribute('result',"%d"%(result))

class Current(XMLDoc):
    ''' requesting for contents of current mafile'''
    def __init__(self,glider,mafile):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","current")
        mafileElement=self.createElement('mafile')
        self.addAttribute(mafileElement,"glider",glider)
        self.addAttribute(mafileElement,"filename",mafile)
        self.addChild(self.packet,mafileElement)

class ResponseCurrent(XMLDoc):
    ''' server response and sending an mafile'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","current")

    def set_content(self,content):
        contentElement=self.createElement('content')
        self.addChild(self.packet,contentElement,content)

class AnyFile(XMLDoc):
    ''' requesting for contents of anyfile'''
    def __init__(self,glider,anyfile):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","file")
        fileElement=self.createElement('file')
        self.addAttribute(fileElement,"glider",glider)
        self.addAttribute(fileElement,"filename",anyfile)
        self.addChild(self.packet,fileElement)

class ResponseAnyFile(XMLDoc):
    ''' server response and sending any file'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","file")

    def set_content(self,content):
        contentElement=self.createElement('content')
        self.addChild(self.packet,contentElement,content)


class Position(XMLDoc):
    ''' requesting for last position of glider'''
    def __init__(self,glider,window):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","position")
        dataElement=self.createElement('position')
        self.addAttribute(dataElement,"glider",glider)
        self.addAttribute(dataElement,"window",window.__str__())
        self.addChild(self.packet,dataElement)

class ResponsePosition(XMLDoc):
    ''' server response with last position'''
    def __init__(self,glider):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","position")
        dataElement=self.createElement('positions')
        self.addAttribute(dataElement,"glider",glider)
        self.addChild(self.packet,dataElement)

    def set_positions(self,tm,lat,lon,last_wpt_lat,last_wpt_lon,
                      c_wpt_lat,c_wpt_lon):
        dataElement=self.packet.getElementsByTagName('positions')[0]
        if tm:
            posElement=self.createElement('position')
            posElement.setAttribute("time",tm.__str__())
            posElement.setAttribute("latitude",lat.__str__())
            posElement.setAttribute("longitude",lon.__str__())
            dataElement.appendChild(posElement)
        if last_wpt_lat:
            wptElement=self.createElement('last_waypoint')
            wptElement.setAttribute("last_latitude",last_wpt_lat.__str__())
            wptElement.setAttribute("last_longitude",last_wpt_lon.__str__())
            dataElement.appendChild(wptElement)
        if c_wpt_lat:
            wptElement=self.createElement('waypoint')
            wptElement.setAttribute("latitude",c_wpt_lat.__str__())
            wptElement.setAttribute("longitude",c_wpt_lon.__str__())
            dataElement.appendChild(wptElement)
                

class Pickup(XMLDoc):
    ''' requesting glider pickup status'''
    def __init__(self,glider,timestamp="now"):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","pickupstatus")
        dataElement=self.createElement('pickupstatus')
        self.addAttribute(dataElement,"glider",glider)
        self.addAttribute(dataElement,"timestamp",timestamp)
        self.addChild(self.packet,dataElement)

class ResponsePickup(XMLDoc):
    ''' server response pickup status glider'''
    def __init__(self,glider):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","pickupstatus")
        dataElement=self.createElement('pickupstatus')
        self.addAttribute(dataElement,"glider",glider)
        self.addChild(self.packet,dataElement)

    def set_pickupstatus(self,status):
        dataElement=self.packet.getElementsByTagName('pickupstatus')[0]
        self.addAttribute(dataElement,"pickupstatus",status)

class Reread(XMLDoc):
    ''' requesting glider reread ma file status'''
    def __init__(self,glider,window):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","rereadstatus")
        dataElement=self.createElement('rereadstatus')
        self.addAttribute(dataElement,"glider",glider)
        self.addAttribute(dataElement,"window",window.__str__())
        self.addChild(self.packet,dataElement)

class ResponseReread(XMLDoc):
    ''' server response reread status glider'''
    def __init__(self,glider):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","rereadstatus")
        dataElement=self.createElement('rereadstatus')
        self.addAttribute(dataElement,"glider",glider)
        self.addChild(self.packet,dataElement)

    def set_rereadstatus(self,status):
        dataElement=self.packet.getElementsByTagName('rereadstatus')[0]
        self.addAttribute(dataElement,"rereadstatus",status)

class FileList(XMLDoc):
    ''' requesting for lof for glider'''
    def __init__(self,glider,timestamp=None):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","filelist")
        dataElement=self.createElement('filelist')
        self.addAttribute(dataElement,"glider",glider)
        if timestamp==None: 
            timestamp=""
        else:
            timestamp="%d"%(int(timestamp))
        self.addAttribute(dataElement,"timestamp",timestamp)
        self.addChild(self.packet,dataElement)

class ResponseFileList(XMLDoc):
    ''' server response with lof'''
    def __init__(self,glider):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","filelist")
        dataElement=self.createElement('filelist')
        self.addChild(self.packet,dataElement)

    def set_lof(self,lof,revisions):
        dataElement=self.packet.getElementsByTagName('filelist')[0]
        for fn in lof:
            fileElement=self.createElement('file')
            fileElement.setAttribute('name',fn)
            if fn in revisions:
                r="%s"%(revisions[fn])
            else:
                r="-1"
            fileElement.setAttribute('revision',r)
            dataElement.appendChild(fileElement)



class GliderList(XMLDoc):
    ''' requesting list of gliders'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","gliderlist")

class ResponseGliderList(XMLDoc):
    ''' server response with list of gliders'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","gliderlist")
        dataElement=self.createElement('gliderlist')
        self.addChild(self.packet,dataElement)

    def set_list_of_gliders(self,gliders):
        dataElement=self.packet.getElementsByTagName('gliderlist')[0]
        for g in gliders:
            fileElement=self.createElement('glider')
            fileElement.setAttribute('name',g)
            dataElement.appendChild(fileElement)


class XMLList(XMLDoc):
    ''' requesting list xmlscripts'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","xmlscripts")

class ResponseXMLList(XMLDoc):
    ''' server response with xmlscripts'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","xmlscripts")
        dataElement=self.createElement('xmlscriptlist')
        self.addChild(self.packet,dataElement)

    def set_list_of_scripts(self,scripts):
        dataElement=self.packet.getElementsByTagName('xmlscriptlist')[0]
        if scripts!=None:
            for k,v in scripts.items():
                for s in v:
                    fileElement=self.createElement('script')
                    fileElement.setAttribute('name',s)
                    fileElement.setAttribute('type',k)
                    dataElement.appendChild(fileElement)


class XMLScript(XMLDoc):
    ''' requesting list xmlscripts'''
    def __init__(self,action,glider,script_name="",
                 script_type="user_scripts"):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","xml")
        self.addAttribute(self.packet,"command",action)
        self.addAttribute(self.packet,"glider",glider)
        self.addAttribute(self.packet,"script_name",script_name)
        self.addAttribute(self.packet,"script_type",script_type)
        

class ResponseXMLScript(XMLDoc):
    ''' server response with xmlscripts'''
    def __init__(self,action):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action",action)

    def set(self,attr,value):
        self.addAttribute(self.packet,attr,value)


class SendLogfile(XMLDoc):
    ''' requesting for sending a log file'''
    def __init__(self,glider,author):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","logfile")
        mafileElement=self.createElement('logfile')
        self.addAttribute(mafileElement,"glider",glider)
        self.addAttribute(mafileElement,"author",author)
        self.addChild(self.packet,mafileElement)


class ResponseLogfile(XMLDoc):
    ''' server response and sending a log file'''
    def __init__(self,logfiletxt,ticket):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","logfile")
        contentElement=self.createElement('content')
        self.addAttribute(contentElement,"ticket",ticket)
        self.addChild(self.packet,contentElement,logfiletxt)

class ReturnLogfile(XMLDoc):
    ''' request for accepting a modified logfile'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","request")
        self.addAttribute(self.packet,"action","returnlogfile")

    def add_content(self,ticket,logfiletxt):
        contentElement=self.createElement('content')
        self.addAttribute(contentElement,"ticket",ticket)
        self.addChild(self.packet,contentElement,logfiletxt)


class ResponseReturnLogfile(XMLDoc):
    ''' server response accepting a modified logfile'''
    def __init__(self):
        XMLDoc.__init__(self)
        self.addAttribute(self.packet,"type","response")
        self.addAttribute(self.packet,"action","returnlogfile")
        resultElement=self.createElement('result')
        self.addChild(self.packet,resultElement)
    
    def set_results(self,accept):
        resultElement=self.packet.getElementsByTagName('result')[0]
        resultElement.setAttribute('accept',"%d"%(accept))


if __name__=='__main__':
    sendmafile=SendMafile('amadeus','yo50.ma','lucas')
    msg = sendmafile()
    reader=XMLReader()
    reader.digest(msg)
    # 
    responseMafile=ResponseMafile('some text\nand more','123123')
    reader2=XMLReader()
    reader2.digest(responseMafile())
    #
    #rrm = ResponseReturnMafile(1,'sometext')
    #
    qs=QueueStatus()
    reader3=XMLReader()
    reader3.digest(qs())
    
