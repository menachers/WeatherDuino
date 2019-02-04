#!/usr/bin/env python
# -*- coding: utf8 -*-
from datetime import datetime
from datetime import timedelta
from email.mime.text import MIMEText
import pytz
import time
import serial
import struct
import sys
from sendmail import sendmail

#For use with raspberry pi plese change to your absolute paths
HeaderName = "/home/pi/WeatherDuino/Transmission_Layout_v10_2.csv"
Logfile = "/home/pi/WeatherDuino/Weatherduino.txt"
WeeWxFile= "/home/pi/WeatherDuino/WeeWx_Exp.txt"
ErrorLog = "/home/pi/WeatherDuino/Weatherduino_Errors.txt"
SerialPort = '/dev/serial0'

#Enables output of all values in console
EnableConsole = 1
#Enables debugging outputs
EnableDebug = 1
#Enable Error log
EnableErrorLog = 1
#Enables E-Mail notifications in case of a lost datastream
#Mail settings have to be performed below
#Please be aware of some routers blocking mails to be sent from unknown servers
EnableMail = 1
#Enables WeeWx Export
EnableWeeWx = 1

#
# declaration of the default mail settings
# The script can send an email to a specified receiver when data transmission stops
#
# mail address of the sender
sender = 'sender@hoster.com'

# mail address of the receiver
receiver = 'receiver@hoster.com'

# fully qualified domain name of the mail server
smtpserver = 'smtp_of_sender'

# username for the SMTP authentication
smtpusername = 'username_of_sender'

# password for the SMTP authentication
smtppassword = 'password_of_sender'

# use TLS encryption for the connection
usetls = True

### --- Do not change anything beyond this point --- ###

#Save starting time in buffer
timebuffer = datetime.now()
mailSent = 0

print "WeatherDuino data reveicer and logger"
print "Version 3.1"
print "Logfile name: ", Logfile
print "Used layout file: ", HeaderName
if EnableErrorLog == 1:
        print "Error logs enabled!"
        print "Logfile can be found here:", ErrorLog
        with open(ErrorLog,'a') as err:
                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Logging script started.\n")
        
print ""
print ("").center(80, "+")
print "Stop logging with ctrl+c"
print ("").center(80, "+")
print ""

#Open layout file
try:
        header = open(HeaderName)
except:
        print"No layout file found. Exiting."
        if EnableErrorLog == 1:
                with open(ErrorLog,'a') as err:
                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " No layout file found. Script aborted.\n")
        sys.exit(1)
structformat = list()
variableLength = list()

print "Start layout file conversion"
#Iterate through all lines of the layout file
for headerrun,headerline in enumerate(header.readlines()):
        #First get the signal names in the columns
        if headerrun == 1:
                names = headerline.strip().split(";")
                #Delete first column
                del names[0]
                #print(headerline)
                #Walk through header elements and check for the "Termination" string to know how much signals of the WeatherDuino logger are expected
                for x in range(len(names)):
                        if names[x] == "Termination":
                                RcvCnt = x+1
                                print "Waiting for " + str(RcvCnt) + " elements from the WeatherDuino logger."
                ExtDataCnt = len(names)-(RcvCnt)
                print "Number of extra signals expected is " + str(ExtDataCnt)+ "."

        #Then get the alias names
        if headerrun == 2:
                alias = headerline.strip().split(";");
                #Delete first column
                del alias[0]
                #print(headerline)
                #When alias names are read, generate corresponding name out of the variable name if no alias is given
                for x in range(len(names)):
                    if alias[x] != '':
                        names[x] = alias[x]
                        #print names

        #Get the info if the signal should be logged
        if headerrun == 3:
                LogExtraData = 0
                loginfo = headerline.strip().split(";");
                #Delete first column
                del loginfo[0]
                #Check if some of the extra signals should be logged
                for x in range(RcvCnt, len(names)):
                        #If yes, raise a flag to know it in the logging state
                        if loginfo[x] == '1':
                                LogExtraData = 1

        #Get the WeeWx alias names
        if headerrun == 4:
                WeeWxAlias = headerline.strip().split(";");
                #Delete first column
                del WeeWxAlias[0]
                #When WeeWx alias names are read, generate corresponding name if no special WeeWx alias name is given
                for x in range(len(names)):
                    if WeeWxAlias[x] == '':
                        WeeWxAlias[x] = names[x]

        #Get the info if the signal should be exported to WeeWx
        if headerrun == 5:
                ExportExtraData = 0
                exportinfo = headerline.strip().split(";");
                #Delete first column
                del exportinfo[0]
                #Check if some of the extra signals should be exported to WeeWx
                for x in range(RcvCnt, len(names)):
                        #If yes, raise a flag to know it in the logging state
                        if exportinfo[x] == '1':
                                ExportExtraData = 1
        #Get the unit group info for WeeWx
        if headerrun == 6:
                exportunitinfo = headerline.strip().split(";");
                #Delete first column
                del exportunitinfo[0]
        
        #parse possible variable types to get format characters for the python struct module
        #Only variables until termination of the layout file to ensure correct calculation of the checksum of the WeatherDuino logger plugin.
        if headerrun == 7:
                vartype = headerline.strip().split(";");
                #Remove first element since it is 
                del vartype[0]
                for x in range(RcvCnt):
                    if vartype[x] == 'uint32_t':
                        structformat.append("L")
                        variableLength.append(4)
                    elif vartype[x] == 'uint16_t':
                        structformat.append("H")
                        variableLength.append(2)
                    elif vartype[x] == 'int16_t':
                        structformat.append("h")
                        variableLength.append(2)
                    elif vartype[x] == 'float':
                        structformat.append("f")
                        variableLength.append(4)
                    elif vartype[x] == 'byte':
                        structformat.append("b")
                        variableLength.append(1)
                    elif vartype[x] == 'uint8_t':
                        structformat.append("B")
                        variableLength.append(1)
                    else:
                        print "Warning vartype " + '"'+ str(vartype[x]) + '"' +" in column " + str(x+1) + " can not be parsed!"
                        if EnableErrorLog == 1:
                                with open(ErrorLog,'a') as err:
                                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Warning vartype " + '"'+ str(vartype[x]) + '"' +" in column " + str(x+1) + " can not be parsed!\n")
                    #print str(vartype[x]) + ' ' + str(variableLength[x])
                bytesum = sum(variableLength)
                print("Sum of all expected bytes from the WeatherDuino logger: " + str(bytesum))
        
        #read scaling factors of all signals
        if headerrun == 8:
                factors = headerline.strip().split(";");
                del factors[0]
                try:
                        factors = [float(x) for x in factors]
                except:
                        print "Scaling factor could not be parsed. Check layout file."
                        print "Use . as decimal separator."
                        print "Aborting now."
                        if EnableErrorLog == 1:
                                with open(ErrorLog,'a') as err:
                                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Scaling factor could not be parsed. Check layout file.\n")
                        sys.exit(1)

        #read corresponding units of all signals
        if headerrun == 9:
                units = headerline.strip().split(";");
                del units[0]
#Close header file
header.close()

#Check signal names which have to be logged and store how many signals should be received originally
CompSignalCount = RcvCnt
#print len(names)
#print len(loginfo)
lognames = []
logunits = []
logfactors = []
expWeeWxAlias = []
expnames = []
expunits = []
expfactors = []

#Create lists for variables to be logged
for n in range(len(names)):
        if loginfo[n] == '1':
                lognames.append(names[n])
                logunits.append(units[n])
                logfactors.append(factors[n])
        if exportinfo[n] == '1':
                expnames.append(names[n])
                expunits.append(exportunitinfo[n])
                expfactors.append(factors[n])
                expWeeWxAlias.append(WeeWxAlias[n])
                
#Open logfile as read and append
try:
        output = open(Logfile,'a+')
except:
        print datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " Output file could not be opened. It seems that it is used by another process. Aborting now."
        if EnableErrorLog == 1:
                with open(ErrorLog,'a') as err:
                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Output file could not be opened. It seems that it is used by another process. Aborting now.\n")
        sys.exit(1)
#Check how much lines are already written in the file
num_lines = sum(1 for line in output)
print ""
if num_lines != 1:
    print "Logfile " + '"' + str(Logfile) + '"' + " successfully read and " + str(num_lines) + " written lines were detected."
else:
    print "Logfile " + '"' + str(Logfile) + '"' + " successfully read and " + str(num_lines) + " written line was detected."
print ""
#print "Check if a new logfile is started or an existing logfile was opened:"
#If there is anything written in the logfile
if num_lines >0:
    #go back to the beginning of the logfile
    output.seek(0)
    firstLine = output.readline().strip().split(";")
    #check if headers are matching
    if(firstLine == lognames):
        print "Existing file detected, new data is appended."
    #print warnings if headers are not matching
    else:
        print ("WARNING!").center(80, "*")
        print "Signal names of the provided logfile and actual layout file do not match."
        print "Please start a new logfile."
        print ("").center(80, "*")
        if EnableErrorLog == 1:
                with open(ErrorLog,'a') as err:
                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Warning! Signal names of actual log file and layout file do not match.\n")
#write new header if file is empty
else:
    print "New file detected, new header is written."
    for n in range(len(lognames)):
        if n == len(lognames)-1:
            output.write(lognames[n] +'\n')
        else:
            if n>=0:
                output.write(lognames[n] +';')
    for n in range(len(lognames)):
        if n == len(lognames)-1:
            output.write(logunits[n] +'\n')
        else:
            if n>=0:
                output.write(logunits[n] +';')
#Close log file
output.close()

#all the prestuff is finished - state machine is starting now
state = 0

#Open try container to provide stop function via keyboard interrupt exception
try:
        #Start endless loop
        while True:
                #Hande first state when serial connection is still closed
                if state == 0:
                        #Prepare everything to start the actual data receiving from serial interface
                        print ""
                        print str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Open serial interface " + str(SerialPort)

                        try:
                                ser=serial.Serial(SerialPort, 115200)
                                print str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Successfully opened."
                                #clear receiving buffer variables
                                data = []
                                ser.flushInput()
                                c = 0
                                #change state to receiving mode
                                state = 1
                        except:
                                print str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Failed to open serial port " + SerialPort + "!"
                                print "Maybe the serial port is not existing or already in use."
                                print "Retry in 5 minutes"
                                if EnableErrorLog == 1:
                                        with open(ErrorLog,'a') as err:
                                                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Faild to open the serial port " + str(SerialPort) + "\n")
                                time.sleep(300)
                        
                #State 1 is the receiving state
                #Read serial port whenever data is received or go to sleep if no data is found in the serial buffer
                if state == 1:
                        try:
                                #check if data is in the serial buffer, if yes get it and append to the buffer array
                                if (ser.inWaiting()>0):
                                        c = ser.read()
                                        if len(c) != 0:
                                                data.append(c)
                                        ErrorCode = 11
                                #otherwise sleep 500ms to save cpu time
                                else:
                                        time.sleep(0.5)
                                        
                                #Check if a complete set of data with correct length and end marker was received
                                if (len(data) >= bytesum and last_c == '\xab' and c == '\xcd'):
                                        ErrorCode = 12
                                        #Calculate CRC only over payload. The last 5 bytes are overhead and not calculated (see layout file)
                                        crc=0
                                        for i in range(bytesum-5):
                                                crc = crc^struct.unpack("B", data[i])[0]

                                        if EnableDebug == 1:
                                                print "Calculated checksum: " +str(crc) + " Expected checksum: " + str(struct.unpack("B", data[-3])[0])

                                        #Get sent crc of the WeatherDuino (see layout file) and check with calculated crc
                                        if(struct.unpack("B", data[-3])[0] == crc):
                                                #if it is true go to state 2
                                                state = 2
                                                if EnableDebug == 1:
                                                        print "Switch to state 2"
                                        #Otherwise discard everything and go back to receiving state.
                                        else:
                                                ErrorCode = 13
                                                if EnableDebug == 1:                                    
                                                        print str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + ": CRC is not matching. (" + str(crc) + "!=" + str(struct.unpack("B", data[-3])[0]) + ")"
                                                        print str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + ": Actual number of payload bytes:" + str(bytesum-5) + "; Number sent by WeatherDuino:" + str(struct.unpack("H", ''.join(data[-5:-4]))[0])
                                                if EnableErrorLog == 1:
                                                        with open(ErrorLog,'a') as err:
                                                                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Checksum error.")
                                                
                                               #value = struct.unpack(structformat[x], ''.join(data[pos:(pos+variableLength[x])]))[0]
                                                #Check if it could be due to wrong bytecount excluding 5 byte overhead
                                                if((bytecount - 5) != (struct.unpack("H", ''.join(data[-5:-4]))[0])):
                                                        print ("WARNING!").center(80, "*")
                                                        print "Expected number of bytes is not matching with byte count sent by WeatherDuino."
                                                        print str(bytecount) + " != " + str(struct.unpack("H", ''.join(data[-5:-4]))[0])
                                                        print "Please check the Com_Transmit plugin and the layout file."
                                                        print "Continuing makes no sense from this point. Script will exit."
                                                        print ("").center(80, "*")
                                                        if EnableErrorLog == 1:
                                                                with open(ErrorLog,'a') as err:
                                                                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Missmatch of expected and transmitted bytes. Check layout file and WeatherDuino plugin.\n")
                                                        sys.exit(1)
                                                data = []
                                
                                #Handle if no valid data via serial can be detected then delete buffer and serial input buffer to start again
                                elif (len(data) > 2*bytesum):
                                        ErrorCode = 14
                                        print str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + ": Can not detect end sequence of buffer. Skipping and cleaning buffer."
                                        if EnableErrorLog == 1:
                                                with open(ErrorLog,'a') as err:
                                                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Could not detect end sequence of received data.\n")
                                        time.sleep(1)
                                        data = []
                                        ser.flushInput()
                
                                last_c = c
                                ErrorCode = 15

                                #Check if there was now logdata sucessfully written since 10 minutes
                                if (datetime.now()-timebuffer) > timedelta(minutes=10) and EnableMail == 1:
                                        if mailSent == 0:
                                                try:
						# call sendmail() and generate a new mail with specified subject and content
                                                        sendmail(str(receiver),'Wetterstation error',str(datetime.now().strftime("%d.%m.%Y %H:%M:%S")) + ' No data is logged since 10 minutes')
                                                        if EnableErrorLog == 1:
                                                                with open(ErrorLog,'a') as err:
                                                                        err.write (str(datetime.now().strftime("%d.%m.%Y %H:%M:%S")) +" Mail sent to " + str(receiver) + "\n")
                                                                        mailSent = 1
                                                except:
                                                        if EnableErrorLog == 1:
                                                                with open(ErrorLog,'a') as err:
                                                                        err.write (str(datetime.now().strftime("%d.%m.%Y %H:%M:%S")) +" Mail could not be sent. \n")
                                                                        mailSent = 1
                                         #else:
                                                 #print "Mail already sent."
                        except:
                                #Something has gone wrong probably at receiving data
                                if EnableDebug == 1:
                                        print "An error has happened during receiving. Waiting 5 minutes and start over again"
                                if EnableErrorLog == 1:
                                        with open(ErrorLog,'a') as err:
                                                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Error receiving data from serial port. Maybe connection was lost. Error code:" + str(ErrorCode) + "\n")
                                time.sleep(300)
                                #Try to close serial port
                                try:
                                        ser.close()
                                except:
                                        if EnableDebug == 1:
                                                print "Serial interface could not be closed"
                                #Start over to state 0 again
                                state = 0

                        extraData = list()
                        ###+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++###
                        ###Do processing of other sources here and store it into a data vector as you want      ###
                        ###Data must be sorted as defined in the layout file                                    ###
                        ###+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++###




                        ###End of User Space++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++###
                        #Check if data in list is valid
                        if len(extraData) != ExtDataCnt:
                                if EnableDebug == 1:
                                        print "Warning: Signal count of extra data defined in layout file and actual signal list are not fitting."
                                        print "Defined signals are " + str(ExtDataCnt) + "! Legth of the signal list is "+ str(len(extraData)) + "!"
                                if EnableErrorLog == 1:
                                        with open(ErrorLog,'a') as err:
                                                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Number of extra signals received and extra signals defined does not match.\n")
                                

                                                                
                #State 2 does the signal processing
                if state == 2:
                        print "State 2 reached"
                        try:
                                #Recover signals of byte array
                                pos = 0
                                #orgname index
                                x=0
                                #Signal array
                                signals = []
                                exp_signals = []
                                #walk through all received signals from WeatherDuino included the ones wich will be dropped (CompSignalCount)
                                while x < CompSignalCount:
                                        #generate signal value from byte array according to byte length and signal position
                                        #struct.unpack funktion is used. Structformat and variable length are already evaluated at the beginng reading the layout file.
                                        value = struct.unpack(structformat[x], ''.join(data[pos:(pos+variableLength[x])]))[0]
                                        #Convert timestamp
                                        if(x==0):
                                                value = datetime.fromtimestamp(value, tz=pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
                                                signals.append(value)
                                                exp_signals.append(value)
                                        #Convert signals
                                        else:
                                                #scale with factor and append to list if signal should be logged which is defined in the layout file
                                                if loginfo[x] == '1':
                                                        signals.append(round(float(value)/float(factors[x]),2))
                                                if exportinfo[x] == '1':
                                                        exp_signals.append(round(float(value)/float(factors[x]),2))
                                        
                                        #move byte index
                                        pos = pos+variableLength[x]
                                        #move orgname index
                                        x = x+1
                                #print 'Unix time :' + str(struct.unpack("L", ''.join(data[0:4]))[0])
                                #print 'Datetime UTC:' + str(datetime.fromtimestamp(int(struct.unpack("L", ''.join(data[0:4]))[0]), tz=pytz.UTC).strftime('%Y-%m-%d %H:%M:%S'))

                                #Now handle all the extra signals received
                                if ExtDataCnt > 0:
                                        for x in range(CompSignalCount, len(names)):
                                                if loginfo[x] == '1':
                                                        try:
                                                                signals.append(round(float(extraData[x-CompSignalCount])/float(factors[x]),2))
                                                        except:
                                                                signals.append(None)
                                                if exportinfo[x] == '1':
                                                        try:
                                                                exp_signals.append(round(float(extraData[x-CompSignalCount])/float(factors[x]),2))
                                                        except:
                                                                exp_signals.append(None)

                                #Print data if console output is enabled
                                if EnableConsole == 1:
                                        print ("").center(80, "-")
                                        for i in range(len(lognames)):
                                                print lognames[i] + ':' + (str(signals[i])).rjust(30-len(lognames[i])) + ' ' + logunits[i]
                                if EnableDebug == 1:
                                        print "Actual timestamp:" + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "; Timestamp at sending:" + str(signals[0])
                                #Empty data buffer
                                data = []
                                #Go to next state where everything is beeing logged
                                state = 3
                        except:
                                if EnableDebug == 1:
                                        print "Something has gone wrong at signal processing this should not be happening."
                                        print "Check your layout file carefully"
                                        print "Trying to start over to receiving state again"
                                if EnableErrorLog == 1:
                                        with open(ErrorLog,'a') as err:
                                                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Error during signal processing.\n")
                                state = 1

                #Write signals data to logfile
                if state == 3:
                        try:
                                #Check if Logfile is still here
                                try:
                                        f = open(Logfile)
                                        f.close()
                                except:
                                        if EnableDebug == 1:
                                                print (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Logfile could not be found.")
                                        if EnableErrorLog == 1:
                                                with open(ErrorLog,'a') as err:
                                                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Logfile disappeared somehow.\n")

                                        output = open(Logfile,'w')
                                        if EnableDebug == 1:
                                                print (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Creating new file with header.")
                                        if EnableErrorLog == 1:
                                                with open(ErrorLog,'a') as err:
                                                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " New logfile created.\n")
                                        for n in range(len(lognames)):
                                                if n == len(lognames)-1:
                                                        output.write(lognames[n] +'\n')
                                                else:
                                                        if n>=0:
                                                                output.write(lognames[n] +';')
                                        for n in range(len(lognames)):
                                                if n == len(lognames)-1:
                                                        output.write(logunits[n] +'\n')
                                                else:
                                                        if n>=0:
                                                                output.write(logunits[n] +';')
                                        #Close log file
                                        output.close()
                                                


                                #Open logfile as append
                                with open(Logfile,'a') as output:
                                        try:
                                                #Walk through all columns
                                                for i in range(len(lognames)):
                                                        #if last column is reached write signal with end of line delimiter
                                                        if i == len(lognames)-1:
                                                                output.write(str(signals[i]) +'\n')
                                                        #otherwise write signal values with column delemiter
                                                        else:
                                                                if i>=0:
                                                                        output.write(str(signals[i]) + ';')
									#Write time of last successfull log entry in buffer
                                                                        timebuffer = datetime.now()
                                                                        mailSent = 1

                                        except:
                                                #If writing with open logfile is not possible strange things are happening and the layout file might be wrong.
                                                print "Something has gone during writing because signal values, signal names or signal factors are mismatching."
                                                print "Continuing makes no sense from this point."
                                                print "Exiting."
                                                if EnableErrorLog == 1:
                                                        with open(ErrorLog,'a') as err:
                                                                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Error during signal writing.\n")
                                                sys.exit(1)
                                #Writing Export file for WeeWx
                                try:
                                        if EnableWeeWx == 1:
                                                with open(WeeWxFile, 'w') as export:
                                                        #Print headerline
                                                        export.write(';')
                                                        for i in range (len(expWeeWxAlias)):
                                                                if i == len(expWeeWxAlias)-1:
                                                                        export.write(str(expWeeWxAlias[i]) + '\n')
                                                                else:
                                                                        export.write(str(expWeeWxAlias[i]) + ';')
                                                        #Print units line
                                                        export.write(';')
                                                        for i in range (len(expunits)):
                                                                if i == len(expunits)-1:
                                                                        export.write(str(expunits[i]) + '\n')
                                                                else:
                                                                        export.write(str(expunits[i]) + ';')

                                                        #convert signals to US units if necessary to ensure correct encoding in WeeWx
                                                        for i in range (len(expunits)):
                                                                #First check temperatures and convert to degree Farenheit
                                                                if expunits[i] == 'group_temperature':
                                                                        exp_signals[i+1] = 1.8*exp_signals[i+1]+32
                                                                if expunits[i] == 'group_length':
                                                                        exp_signals[i+1] = exp_signals[i+1]/2.54
                                                                if expunits[i] == 'group_pressure':
                                                                        exp_signals[i+1] = exp_signals[i+1]/33.864    
                                                                if expunits[i] == 'group_speed':
                                                                        exp_signals[i+1] = exp_signals[i+1]/1.609


                                                        #Walk through all signals and write them to the export file
                                                        for i in range(len(expnames)+1):    
                                                                #write to file
                                                                #if last column is reached write signal with end of line delimiter
                                                                if i == len(expnames):
                                                                        export.write(str(exp_signals[i]) + '\n')
                                                                        #print(str(exp_signals[i]) +'\n')
                                                                #otherwise write signal values with column delemiter
                                                                else:
                                                                        if i>=0:
                                                                                export.write(str(exp_signals[i]) + ';')                                                               
                                except:
                                        if EnableDebug == 1:
                                                print "Error writing WeeWx export"
                                        if EnableErrorLog == 1:
                                                with open(ErrorLog,'a') as err:
                                                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Error writing the WeeWx export file.\n")
                                                                

                                #Jump back to receiving mode in state 1
                                state = 1

                                
                        except:
                                if EnableDebug == 1:
                                        print "File could not be opened trying to write again in 10 seconds."
                                if EnableErrorLog == 1:
                                        with open(ErrorLog,'a') as err:
                                                err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Error opening the log file.\n")
                                time.sleep(10)

except KeyboardInterrupt:
        ser.close()
        print str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + ": Logging stopped and serial port closed."
        if EnableErrorLog == 1:
                with open(ErrorLog,'a') as err:
                        err.write (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " Script ended with keystroke.\n")
        sys.exit(0)

