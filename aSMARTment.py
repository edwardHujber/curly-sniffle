# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import Tkinter
from subprocess import PIPE, Popen
from time import sleep
import MySQLdb
import os

def readTempRaw():
    #f = open(device_file, 'r')
    #lines = f.readlines()
    lines =('50 05 4b 46 7f ff 0c 10 1c : crc=1c YES', '50 05 4b 46 7f ff 0c 10 1c t=13456') ## if not running on the pi
    #f.close()
    return lines

def readTemp():
    lines = readTempRaw()
    while lines[0].strip()[-3:] != 'YES':
        sleep(0.1)
        lines = readTempRaw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string)/1000.0
        return temp_c

def CoordFromDB(sPP,t,c):
    timeWidOfScreen = chartW*sPP ## how much time fits on chart, in s
    ago=t-timedelta(seconds=timeWidOfScreen)
    c.execute("DELETE FROM tempdat WHERE tDateTime <  NOW()-INTERVAL 2 DAY")
    c.execute("SELECT temperature FROM tempdat WHERE tDateTime >= '{}'".format(ago))
    maxTemp = max(list(c))[0]
    minTemp = min(list(c))[0]
    tempRange = maxTemp-minTemp
    tempPad=3
    labelYtemp = [round(minTemp),round((maxTemp+minTemp)/2),round(maxTemp)]
    labelYpos=[chartH-((chartH/(tempRange+2*tempPad))*(round(minTemp)-(minTemp-tempPad))),
               chartH-((chartH/(tempRange+2*tempPad))*(round((maxTemp+minTemp)/2)-(minTemp-tempPad))),
               chartH-((chartH/(tempRange+2*tempPad))*(round(maxTemp)-(minTemp-tempPad)))]
    c.execute("SELECT tDateTime,temperature FROM tempdat WHERE tDateTime >= '{}' ORDER BY tDateTime ASC".format(ago))
    coords = []
    labelXpos=[]
    labelXtime=[]
    lastTimeLabel=0
    firstRecord=True
    for read in c.fetchall():
        tempTime = datetime.strptime('{}'.format(read[0]), '%Y-%m-%d %H:%M:%S')
        tDiff =(t-tempTime).total_seconds()
        x=chartW-(tDiff/sPP)
        y=chartH-((chartH/(tempRange+2*tempPad))*(read[1]-(minTemp-tempPad))) ## (chart Y range) * (min temp value)    
        if(firstRecord|(((tempTime.hour/chartLabelEveryHour)==(tempTime.hour//chartLabelEveryHour)) & (tempTime.hour!=lastTimeLabel))):
            firstRecord=False
            lastTimeLabel=tempTime.hour
            labelXpos.append(x)
            labelXtime.append(tempTime.strftime("%-I%p").lower())
        coords.append(int(round(x)))
        coords.append(int(round(y)))
    return coords,labelYpos,labelYtemp,labelXpos,labelXtime

def incSP():
    if tempF:
        setPointIV.set(setPointIV.get()+(5.0/9.0))
    else:
        setPointIV.set(setPointIV.get()+1)
    

def decSP():
    if tempF:
        setPointIV.set(setPointIV.get()-(5.0/9.0))
    else:
        setPointIV.set(setPointIV.get()-1)

def updateSP(*args):
    dispSP.configure(text="{}°{}".format(int(CorF(setPointIV.get())),unitSV.get()))

def tempLow():
    dispTemp.configure(fg="blue",activeforeground="blue")
    dispUnit.configure(fg="blue")

def tempHigh():
    dispTemp.configure(fg="red",activeforeground="red")
    dispUnit.configure(fg="red")
    
def tempOK():
    dispTemp.configure(fg="black",activeforeground="black")
    dispUnit.configure(fg="black")

def setCorF():
    global tempF
    tempF = not(tempF)
    dispTemp.configure(text="%.1f" % CorF(room_temp))
    if tempF:
        setPointIV.set((round(setPointIV.get()*9/5+32)-32)*5/9)
        unitSV.set("F")
    else:
        setPointIV.set(round(setPointIV.get()))
        unitSV.set("C")

def CorF(C):
    if tempF:
        return C * 9.0 / 5.0 + 32.0
    else:
        return C

def updateUnit(*args):
    dispSP.configure(text="{}°{}".format(int(CorF(setPointIV.get())),unitSV.get()))
    dispUnit.configure(text="°{}".format(unitSV.get()))
    refreshChart(new_coords)

def refreshChart(cords):
    Xaxis.itemconfigure(Xlab1,text="")
    Xaxis.itemconfigure(Xlab2,text="")
    Xaxis.itemconfigure(Xlab3,text="")
    Xaxis.itemconfigure(Xlab4,text="")
    Xaxis.itemconfigure(Xlab5,text="")

    XlabLib={"1":Xlab1,"2":Xlab2,"3":Xlab3,"4":Xlab4,"5":Xlab5}
    i=0
    for each in zip(cords[3],cords[4])[1:]:
        i+=1
        Xaxis.coords(XlabLib[str(i)],each[0],0)
        Xaxis.itemconfigure(XlabLib[str(i)],text=each[1])
        
    Yaxis.coords(Ytik1,0,cords[1][0],2,cords[1][0])
    Yaxis.coords(Ytik3,0,cords[1][2],2,cords[1][2])

    Yaxis.coords(Ylab1,3,cords[1][0])
    Yaxis.coords(Ylab3,3,cords[1][2])
    
    Yaxis.itemconfigure(Ylab1,text="{}°{}".format(int(CorF(cords[2][0])),unitSV.get()))
    Yaxis.itemconfigure(Ylab3,text="{}°{}".format(int(CorF(cords[2][2])),unitSV.get()))

    chart.coords(datLine,*cords[0])

def tempCheck():
    global room_temp_list
    global prevGraphUDtime
    time= datetime.now()
    room_temp = readTemp()
    room_temp_list.append(room_temp)
    dispTemp.configure(text="%.1f" % CorF(room_temp))
    if (time - prevGraphUDtime)>timedelta(0,secPerPix,0):
        prevGraphUDtime = time
        curs.execute("INSERT INTO tempdat values(NOW(), {})".format(sum(room_temp_list)/float(len(room_temp_list))))
        db.commit()
        new_coords=CoordFromDB(secPerPix,time,curs)
        refreshChart(new_coords)
        room_temp_list=[]

    if room_temp < setPointIV.get()-tolerance:
        tempLow()
    elif room_temp > setPointIV.get()+tolerance:
        tempHigh()
    else:
        tempOK()
    topFrame.after(500,tempCheck)
    

## Sets up the DS18B20 interface
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
device_file= "/sys/bus/w1/devices/28-0416562a91ff/w1_slave"

##This is the touchscreen resolution
screenW = 240
screenH = 320
screenDims = "{}x{}".format(screenW,screenH)

chartH = 80
chartW = 200
secPerPix = 150
prevGraphUDtime= datetime.now()-timedelta(0,secPerPix,0)

setPoint = 23
tolerance = 2
tempF = False

chartLabelEveryHour = 2.0
room_temp_list=[]

db = MySQLdb.connect("localhost","monitor","rasp","temps")
curs=db.cursor()

## Top Frame
topFrame = Tkinter.Tk()
#topFrame.config(cursor='none')
topFrame.geometry(screenDims)
#topFrame.overrideredirect(True) ##removes titlebar, borders
setPointIV = Tkinter.DoubleVar()
setPointIV.set(setPoint)
setPointIV.trace("w",updateSP)
unitSV = Tkinter.StringVar()
unitSV.set("C")
unitSV.trace("w",updateUnit)

## Temperature Frame
tempFrame = Tkinter.Frame(topFrame)
tempFrame.grid(row=0)
dispTemp = Tkinter.Button(tempFrame, text="", command=setCorF,font=("Helvetica",64),pady=0,bd=0,activebackground='gray85')
dispTemp.grid(row=0,column=0)
dispUnit = Tkinter.Label(tempFrame, text="°{}".format(unitSV.get()), font=("Helvetica",18), anchor="nw",height=2)
dispUnit.grid(row=0,column=1)

## Chart Frame
chartFrame = Tkinter.Frame(topFrame)
chartFrame.grid(row=1)
chart = Tkinter.Canvas(chartFrame, bg="gray85", height=chartH,width=chartW,highlightthickness=0)
chart.grid(row=0,column=0)
datLine= chart.create_line(0,0,100,100, width=2, smooth="FALSE")
axesLines=chart.create_line(0,chartH-1,chartW-1,chartH-1,chartW-1,0,width=1)

Xaxis= Tkinter.Canvas(chartFrame, bg="gray85",width=screenW, height=30,highlightthickness=0)
Xaxis.grid(row=1,column=0, columnspan=2)
Xlab1 = Xaxis.create_text(0,0,text = "",angle=-30,anchor='nw')
Xlab2 = Xaxis.create_text(0,0,text = "",angle=-30,anchor='nw')
Xlab3 = Xaxis.create_text(0,0,text = "",angle=-30,anchor='nw')
Xlab4 = Xaxis.create_text(0,0,text = "",angle=-30,anchor='nw')
Xlab5 = Xaxis.create_text(0,0,text = "",angle=-30,anchor='nw')

Yaxis= Tkinter.Canvas(chartFrame, bg="gray85",height=chartH, width=40,highlightthickness=0)
Yaxis.grid(row=0,column=1)
Ylab1 = Yaxis.create_text(0,0,text = "",anchor='w')
Ylab2 = Yaxis.create_text(0,0,text = "",anchor='w')
Ylab3 = Yaxis.create_text(0,0,text = "",anchor='w')
Ytik1 = Yaxis.create_line(0,0,0,0,width=1)
Ytik2 = Yaxis.create_line(0,0,0,0,width=1)
Ytik3 = Yaxis.create_line(0,0,0,0,width=1)

## Setpoint Frame
spFrame = Tkinter.Frame(topFrame)
spFrame.grid(row=2)
dispSP = Tkinter.Label(spFrame, text="{}°C".format(int(setPointIV.get())),font=("Helvetica",14))
dispSP.grid(row=1)

spUp = Tkinter.Button(spFrame,command=incSP, text="UP",font=("Helvetica",14))
spUp.grid(row=0)

spDown = Tkinter.Button(spFrame,command=decSP, text="DOWN",font=("Helvetica",14))
spDown.grid(row=2)

## Information Frame
##infoFrame = Tkinter.Frame(topFrame, bg="green")
##infoFrame.grid()
##dispInfo1 = Tkinter.Label(infoFrame, text="", font=("Helvetica",15))
##dispInfo1.grid(row=1,column=3)
##dispInfo2 = Tkinter.Label(infoFrame, text="", font=("Helvetica",15))
##dispInfo2.grid(row=2,column=1)



## Live update loop



topFrame.after(500,tempCheck)
topFrame.mainloop()
