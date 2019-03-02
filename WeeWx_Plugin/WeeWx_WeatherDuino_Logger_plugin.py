import syslog
import weewx
from datetime import datetime
from time import strptime
from time import mktime
from weewx.wxengine import StdService
import weewx.units

#First read units from unit line of the export file
filename = '/home/pi/WeatherDuino/WeeWx_Exp.txt'
with open(filename) as f:
    for line,row in enumerate(f.readlines()):
        if line == 0:
            names = row.strip().split(";")
        if line == 1:
            unit_groups = row.strip().split(";")

#Add variable names to unit groups
for n in range(len(names)-1):
    if str(unit_groups[n+1]) != 'none':
        weewx.units.obs_group_dict[str(names[n+1])] = str(unit_groups[n+1])
    
weewx.units.USUnits['group_gas_concentration'] = 'ppm'
weewx.units.MetricUnits['group_gas_concentration'] = 'ppm'
weewx.units.MetricWXUnits['group_gas_concentration'] = 'ppm'
weewx.units.default_unit_format_dict['ppm']  = '%.0f'
weewx.units.default_unit_label_dict['ppm']  = ' ppm'

weewx.units.USUnits['group_dust'] = 'microgramm_per_meter_cubic'
weewx.units.MetricUnits['group_dust'] = 'microgramm_per_meter_cubic'
weewx.units.MetricWXUnits['group_dust'] = 'microgramm_per_meter_cubic'
weewx.units.default_unit_format_dict['microgramm_per_meter_cubic']  = '%.1f'
weewx.units.default_unit_label_dict['microgramm_per_meter_cubic']  = ' \xce\xbcg/m\xc2\xb3'

####################################################################################

class WeeWxService(StdService):
    def __init__(self, engine, config_dict):
        super(WeeWxService, self).__init__(engine, config_dict)      
        d = config_dict.get('WeatherDuino_logger_service', {})
        self.filename = d.get('filename', '/home/pi/WeatherDuino/WeeWx_Exp.txt')
        syslog.syslog(syslog.LOG_INFO, "WeatherDuino: using %s" % self.filename)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.read_file)
    
    def read_file(self, event):
        try:
            #Read data from WeatherDuino Logger output txt file
            with open(self.filename) as f:
                for line,row in enumerate(f.readlines()):
                    if line == 0:
                        names = row.strip().split(";")
                    if line == 1:
                        units = row.strip().split(";")
                    if line == 2:
                        values = row.strip().split(";")

            #Define path of safefile
            safefile = '/home/pi/WeatherDuino/Rain_tmp.txt'
            try:
                with open(safefile,'r') as tmp:
                        for line,row in enumerate(tmp.readlines()):
                            if line == 0:
                                tmprain = row.strip().split(";")
                            else:
                                tmprain=[]
                print "Safefile file opened and read " + str(len(tmprain)) + " entries."
            except:
                tmprain=[]
                        
            #Read timestamp of data and convert it
            timestamp = strptime(values[0], '%Y-%m-%d %H:%M:%S')
            dt = datetime.fromtimestamp(mktime(timestamp))
            #Check if read data is not older than 3 minutes
            if (datetime.now()-dt).total_seconds() < 180:
                syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: valid values found")

                #Create index pointer for rain buffer vector
                rainind=0

                for n in range(len(values)-1):
                    #Convert transmitted total rain value to rain delta since last WeeWx import
                    if units[n+1] == 'group_rain':
                        #Check if the safe file contains enough entries
                        if rainind < len(tmprain):
                            #if yes calculate the rain difference and store the new rain value into the buffer
                            try:
                                deltarain = float(values[n+1]) - float(tmprain[rainind])
                                tmprain[rainind] = float(values[n+1])
                            except:
                                deltarain = None
                        #If there are not enough entries - for which reason ever - write None to WeeWx and add a entry to the buffer
                        else:
                            deltarain = None
                            tmprain.append(values[n+1])

                        #Check the integrity of the data maybe the rain counter of the WeatherDuino has run over or other strange things happened causing ghost rain
                        if deltarain < 0 or deltarain > 30:
                            deltarain = None
                        #Add the value to the WeeWx database
                        event.record[str(names[n+1])] = deltarain
                        #Shift rain index to handle more rain signals
                        rainind = rainind + 1
                    #Handle all other signals
                    else:
                        event.record[str(names[n+1])] = float(values[n+1])

                #Write actual rain values to buffer file
                with open(safefile, 'w') as tmp:
                    for i in range (len(tmprain)):
                        if i == len(tmprain)-1:
                            tmp.write(str(tmprain[i]) + '\n')
                        else:
                            tmp.write(str(tmprain[i]) + ';')
                        
            #Else throw an exception
            else:
                syslog.syslog(syslog.LOG_ERR, "WeatherDuino Logger: Data is too old. Check logging addon!")

        except Exception, e:
            syslog.syslog(syslog.LOG_ERR, "WeatherDuino Logger: Error reading values")


#################################################################################
import schemas.wview
filename = '/home/pi/WeatherDuino/WeeWx_Exp.txt'

with open(filename) as f:
	for line,row in enumerate(f.readlines()):
		if line == 0:
			names = row.strip().split(";")
schema_WeatherDuino = schemas.wview.schema
for n in range(len(names)-1):
	schema_WeatherDuino = schema_WeatherDuino + [(str(names[n+1]), 'REAL')]
