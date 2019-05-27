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
        self.last_rain = [None, None, None, None]
    
    def read_file(self, event):
        error_ind = -1
        archive_dt = 1
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

            syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: Unit of record to be archived: " + str(event.record['usUnits']))                        

            #Read timestamp of data and convert it
            timestamp = strptime(values[0], '%Y-%m-%d %H:%M:%S')
            dt = datetime.fromtimestamp(mktime(timestamp))
            #Read timestamp of the record and convert it
            archive_dt = datetime.fromtimestamp(event.record['dateTime'])
            syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: Archive timestamp: " + str(archive_dt))
            syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: Data timestamp: " + str(dt))
            
            #Check if read data is not older than 3 minutes
            #if (datetime.now()-dt).total_seconds() < 180:
            if (dt - archive_dt).total_seconds() < 180:
                syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: Valid values found")

                #Create index pointer for last_rain buffer list and error handling
                rainind=0
                error_ind = 0
                deltarain = 0

                for n in range(len(values)-1):
                    error_ind = n

                    #First convert data to target units if necessary
                    if event.record['usUnits'] == 1:
                        #syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: Converting relevant signals to target unit")                        

                        #First check temperatures and convert to degree Farenheit
                        if units[n+1] == 'group_temperature':
                                values[n+1] = 1.8*float(values[n+1])+32
                        if units[n+1] == 'group_length':
                                values[n+1] = float(values[n+1])/2.54
                        if units[n+1] == 'group_pressure':
                                values[n+1] = float(values[n+1])/33.864    
                        if units[n+1] == 'group_speed':
                                values[n+1] = float(values[n+1])/1.609
                        if units[n+1] == 'group_rain':
                                values[n+1] = float(values[n+1])/25.4
                        if units[n+1] == 'group_rainrate':
                                values[n+1] = float(values[n+1])/25.4
                    
                    #Convert transmitted total rain value to rain delta since last WeeWx import
                    if units[n+1] == 'group_rain':
                        #Check if the safe file contains enough entries
                        if rainind < len(self.last_rain):
                            #if yes calculate the rain difference and store the new rain value into the buffer
                            try:
                                #Handle if variable is None after a restart of WeeWx
                                if self.last_rain[rainind] != None:
                                    deltarain = float(values[n+1]) - self.last_rain[rainind]
                                else:
                                    deltarain = None

                                self.last_rain[rainind] = float(values[n+1])
                            except:
                                deltarain = None
                        #If there are not enough entries - for which reason ever - write None to WeeWx and add a entry to the buffer
                        else:
                            deltarain = None

                        #Check the integrity of the data maybe the rain counter of the WeatherDuino has run over or other strange things happened causing ghost rain
                        if deltarain < 0 or deltarain > 30:
                            deltarain = None
                        #Add the value to the WeeWx database
                        #syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: " + str(names[n+1]) + ": " + str(deltarain))
                        event.record[str(names[n+1])] = deltarain
                        #Shift rain index to handle more rain signals
                        rainind = rainind + 1
                    #Handle all other signals
                    else:
                        event.record[str(names[n+1])] = float(values[n+1])
                        #syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: " + str(names[n+1]) + ": " + str(values[n+1]))
                        
            #Else throw an exception
            else:
                syslog.syslog(syslog.LOG_ERR, "WeatherDuino: Data is too old. Check logging addon!")

        except Exception, e:
            syslog.syslog(syslog.LOG_ERR, "WeatherDuino: Processing error at positon " + str(error_ind)+ ": " + str(names[error_ind+1]))


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
schema_WeatherDuino = schema_WeatherDuino + [('lightning_strikes', 'REAL')]
schema_WeatherDuino = schema_WeatherDuino + [('avg_distance', 'REAL')]
