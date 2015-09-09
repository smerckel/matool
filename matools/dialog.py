import glob
import os
import re
from . import timeconversion

class Event(object):
    def __init__(self,pattern):
        self.regex=re.compile(pattern)
        self.timeregex=re.compile("Curr Time.*MT")
        self.timestamp=0
        self.event_timestamp=0

    def set_timestamp(self,line):
        datestr=" ".join(line.split()[3:7])
        self.timestamp=timeconversion.strptimeToEpoch(datestr,"%b %d %H:%M:%S %Y")

    def process(self,line):
        if self.timeregex.match(line):
            self.set_timestamp(line)
        elif self.regex.match(line):
            self.event_timestamp=self.timestamp


class DialogMonitor(object):
    def __init__(self,path):
        self.path=path
        self.cache=[]
        self.events={}
    
    def get_lof(self):
        fns=glob.glob(os.path.join(self.path,"logs","*.log"))
        fns.sort()
        return fns

    def add_event(self,event,pattern):
        self.events[event]=Event(pattern)

    def read(self):
        for fn in self.get_lof():
            if fn not in self.cache:
                self.parse(fn)
                self.cache.append(fn)

    def parse(self,fn):
        fd=open(fn,'r')
        lines=fd.readlines()
        fd.close()
        for event in list(self.events.values()):
            for line in lines:
                event.process(line)

if __name__=="__main__":        
    d=DialogMonitor("/home/lucas/dockserver/gliders/sebastian")
    d.add_event("mafiles re-read","MAFILES will be re-read")
    d.read()
    print(d.events["mafiles re-read"].event_timestamp)

            
