#!/usr/bin/python

import glob
import os
import timeconversion
import sys

eval(input("Supply glider logs directory as 1st argument. Enter to continue"))

HistoryFile='history.txt'
LogDir='/home/lucas/samba/gliders/amadeus/logs'
LogDir=sys.argv[1]

fns=glob.glob(os.path.join(LogDir,"*.log"))
fns.sort()

logtxt=[]
for fn in fns:
    fd=open(fn)
    logtxt+=fd.readlines()
    fd.close()
# keep only Curr TIme and MAFILES will be re-read lines
logtxt=[i for i in logtxt if "Curr" in i or "MAFILES will be re-read" in i]

# index the MAFILES lines
indx=[k for k,v in enumerate(logtxt) if v.startswith("MAFILES")]

mafiles_txt=[]
for i in indx:
    timestr=logtxt[i-1]
    timestr=timestr.replace("Time:","Time|").replace("MT:","|")
    s=timestr.split("|")[1].strip()
    mafiles_txt.append("%s: MAFILES reread.\n"%(s))

fd=open(HistoryFile)
history_txt=fd.readlines()
fd.close()
history_txt+=mafiles_txt

def cmp(x,y):
    x0=x[:24]
    y0=y[:24]
    action0=x[26:33]
    action1=y[26:33]
    t0=timeconversion.strptimeToEpoch(x0,"%a %b %d %H:%M:%S %Y")
    t1=timeconversion.strptimeToEpoch(y0,"%a %b %d %H:%M:%S %Y")
    if abs(t0-t1)<30*60:# all same minute
        r=int(action0=='MAFILES')-int(action1=='MAFILES')
    else:
        r=int(t0>t1)-int(t0<t1)
    return r

history_txt.sort(cmp=cmp)

answer=eval(input("I am going to overwrite the log file. Ok?"))
if answer=="y" or answer=="Y":
    fd=open(HistoryFile,'w')
    fd.writelines(history_txt)
    fd.close()
    print("Done.")
else:
    print("Done nothing.")
