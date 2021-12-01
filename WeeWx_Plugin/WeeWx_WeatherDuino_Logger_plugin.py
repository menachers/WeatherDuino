import weewx
from datetime import datetime
from time import strptime
from time import mktime
from weewx.wxengine import StdService
import weewx.units

#import logging capabilities
try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger('WeatherDuino')
    version = 4

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog
    version = 3

    def logmsg(level, msg):
        # Replace '__name__' with something to identify your application.
        syslog.syslog(level, '%s:' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

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
        logdbg("Unit " + str(unit_groups[n+1]) + " attached to signal " + str(names[n+1]))

#weewx.units.obs_group_dict['rain_RG11'] = 'group_rain'
#logdbg(Unit " + 'group_rain' + " attached to signal " + 'rain_RG11')

if version == 3:
    #if you also have the plugin for the lightning sensor installed
    weewx.units.obs_group_dict['lightning_strike_count'] = 'group_count'
    weewx.units.obs_group_dict['lightning_distance'] = 'group_distance'
        
    weewx.units.USUnits['group_fraction'] = 'ppm'
    weewx.units.MetricUnits['group_fraction'] = 'ppm'
    weewx.units.MetricWXUnits['group_fraction'] = 'ppm'
    weewx.units.default_unit_format_dict['ppm']  = '%.0f'
    weewx.units.default_unit_label_dict['ppm']  = ' ppm'

    weewx.units.USUnits['group_concentration'] = 'microgram_per_meter_cubed'
    weewx.units.MetricUnits['group_concentration'] = 'microgram_per_meter_cubed'
    weewx.units.MetricWXUnits['group_concentration'] = 'microgram_per_meter_cubed'
    weewx.units.default_unit_format_dict['microgram_per_meter_cubed']  = '%.1f'
    weewx.units.default_unit_label_dict['microgram_per_meter_cubed']  = ' \xce\xbcg/m\xc2\xb3'

    weewx.units.USUnits['group_illuminance'] = 'lux'
    weewx.units.MetricUnits['group_illuminance'] = 'lux'
    weewx.units.MetricWXUnits['group_illuminance'] = 'lux'
    weewx.units.default_unit_format_dict['lux']  = '%.0f'
    weewx.units.default_unit_label_dict['lux']  = ' lux'

####################################################################################

class WeeWxService(StdService):
    def __init__(self, engine, config_dict):
        super(WeeWxService, self).__init__(engine, config_dict)      
        d = config_dict.get('WeatherDuino_logger_service', {})
        self.filename = d.get('filename', '/home/pi/WeatherDuino/WeeWx_Exp.txt')
        loginf("using %s" % self.filename)
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
                        unittype = row.strip().split(";")
                    if line == 3:
                        values = row.strip().split(";")

            logdbg("Unit of record to be archived: " + str(event.record['usUnits']))                        

            #Read timestamp of data and convert it
            timestamp = strptime(values[0], '%Y-%m-%d %H:%M:%S')
            dt = datetime.fromtimestamp(mktime(timestamp))
            #Read timestamp of the record and convert it
            archive_dt = datetime.fromtimestamp(event.record['dateTime'])
            logdbg("Archive timestamp: " + str(archive_dt))
            logdbg("Data timestamp: " + str(dt))
            
            #Check if read data is not older than 3 minutes
            #if (datetime.now()-dt).total_seconds() < 180:
            if (dt - archive_dt).total_seconds() < 180:
                logdbg("Valid values found")

                #Create index pointer for last_rain buffer list and error handling
                rainind=0
                deltarain = 0

                for n in range(len(values)-1):
                    error_ind = n

                   
                    #Convert transmitted total rain value to rain delta since last WeeWx import
                    if units[n+1] == 'group_rain' and names[n+1] != 'snowDepth':
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
                        if deltarain != None and (deltarain < 0 or deltarain > 30):
                            deltarain = None

                        #Try to perform an automatic unit conversion into the chosen target system in WeeWx
                        try:
                            #Create temporary value tuple for WeeWx integrated unit conversion
                            temp_vt = weewx.units.ValueTuple(deltarain, str(unittype[n+1]), str(units[n+1]))              
                            #Augment rain data to archive record with the appropriately converted value
                            #logdbg(str(names[n+1]) + ": " + str(deltarain))
                            event.record[str(names[n+1])] = weewx.units.convertStd(temp_vt, event.record['usUnits'])[0]
                        #if the automatic conversion fails, just augment the data as it is and rise an error
                        except:
                            event.record[str(names[n+1])] = deltarain
                            logerr("Not able to convert the signal " + str(names[n+1])+". Check if unit group " + str(units[n+1]) + " contains an unit type called " + str(unittype[n+1]) + ".")
                            
                        #Shift rain index to handle more rain signals                        
                        rainind = rainind + 1
                    #Handle all other signals
                    else:
                        #Try to perform an automatic unit conversion into the chosen target system in WeeWx
                        if values[n+1] != "None":  
                            try:     
                                #Create temporary value tuple for WeeWx integrated unit conversion
                                temp_vt = weewx.units.ValueTuple(float(values[n+1]), str(unittype[n+1]), str(units[n+1]))
                                #Augment data to archive record with the appropriately converted value
                                event.record[str(names[n+1])] = weewx.units.convertStd(temp_vt, event.record['usUnits'])[0]
                                #syslog.syslog(syslog.LOG_DEBUG, "WeatherDuino: " + str(names[n+1]) + ": " + str(values[n+1]))
                            #if the automatic conversion fails, just augment the data as it is and rise an error
                            except:
                                event.record[str(names[n+1])] = float(values[n+1])

                                logerr("Not able to convert the signal " + str(names[n+1])+". Check if unit group " + str(units[n+1]) + " contains an unit type called " + str(unittype[n+1]) + ".")
                        else:
                            event.record[str(names[n+1])] = None
                            
                #loginf("Augmented record with timestamp " + str(archive_dt))
                            
            #Else throw an exception that the data is too old
            else:
                logerr("Timestamp of augmented data is " + str(dt) + ". Timestamp of actual record is " + str(archive_dt) + ". This is too old and nothing is done. Check logging addon!")

        except(Exception):
            if error_ind >= 0:
                logerr("Processing error at positon " + str(error_ind)+ ": " + str(names[error_ind+1]))
            else:
                logerr("Initialization error of files. Check correct export file generation in logging script if this keeps happening.")


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
#if you also have the plugin for the lightning sensor installed
if version == 3:
    schema_WeatherDuino = schema_WeatherDuino + [('lightning_strike_count', 'REAL')]
    schema_WeatherDuino = schema_WeatherDuino + [('lightning_distance', 'REAL')]
