/***************************************************************************
           WeatherDuino Laser snow measurement software

  Snow height measurement measures a height with a laser ranging device from a mounting position to get the actual snow height or whatever should be measured.
  The mounting height is stored at the EEPROM and can be set or overwritten with the acutal measured value by pushing the tare button.
  Be careful, that for correct calculation of the tare value the right mounting angle has already do be specified and the underground has to be free of snow.

  The range of the transmitted data for the snow height is between 0 and 100 [cm] or [dm] be careful that measurements below or above that values are cut.

  The measurement results are provided via I²C over a emulated HU21D/SHT temperature sensor.

  Board compatibility              : snow height measurement >4.0

  TX Boards compatibility          : Each WeatherDuino TX Board supporting the HU21D temperature sensor

  Software Version      : 5.0 (Compile using Arduino IDE 1.8.3 or newer)
  Version Released date : 12/29/2019
  Last revision date    : 12/29/2019
  Licence               : GNU GPLv3
  Author                : engolling
  Support Forum         : http://www.meteocercal.info/forum

  Always check user configurable options at Config_Options.h tab

  -------------------------------------------------------------------------------------
          >>>>>>>>>>>> About Copyrights <<<<<<<<<<<<<<<
  -------------------------------------------------------------------------------------
  License:GNU General Public License v3.0

    WeatherDuino Pro2 Snow height measurement software
    Copyright (C) 2019  engolling - www.meteocercal.info/forum

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*************************************************************************************/


#include <Adafruit_SleepyDog.h>
#include <SoftwareSerial.h>
#include <Wire.h>
#include "Config_Options.h"
#include "RunningMedian.h"
#include <EEPROM.h>
//Pins must support PCINT. Do not change since they are routed on the PCB
SoftwareSerial Laser(6, 7); // RX, TX

//Define pin for tare function, when setting to low level
#define TAREPIN 8

//Define LED pin for I²C communication indicator. Do not change the pin.
#define LED 9

//Define after how much millies the reception of the laser data timeouts
#define TIMEOUT 10000

//init global variables
uint32_t LastMeasurement = 0;   // holds millis of last measurement for timing
uint32_t RcvTimeout = 0;        // controls timeout after no data is received from LASER after request
uint8_t ErrMsg = 0;             // controls that error message is only sent once
int i2cRequest;                 // holds byte of i2c requested variable
int eeAddress = 0;              // holds EEprom adress of stored tare value

//Variable for state machine
uint8_t state = 1;              // 1 = starting up, 0 = waiting for answer, 2 = filling filter, 3 = normal operation
// I2C messages are only sent in state 3
uint8_t initRunCtr = 0;         // Counter for initially filling the median filter
uint8_t state_trigger = 0;      // timing variable for reading status message in between the distance readings

int setupHeight;                // height in mm where the sensor is mounted over ground

volatile int temperature = -1;  // buffer for status temperature
volatile int voltage = -1;      // buffer for status voltage
volatile int distance;          // buffer variable holding the actually evaluated distance to ground

#if LASER_DEVICE == 1           // buffer variables only for HIREED device
char inputBuffer[20];
uint8_t a = 0;
uint8_t digitPtr = 0;
String buf;
String resultString;
#endif

#if LASER_DEVICE == 2
union laser_send_data_t {
  struct bytes_t {
    uint8_t preamble;
    uint8_t command;
    uint8_t data[3];
    uint8_t check_code[2];
  } bytes;
  uint8_t array[sizeof(bytes)];
} laser_send_data;

union laser_rcv_data_t {
  struct bytes_t {
    uint8_t preamble;
    uint8_t command;
    uint8_t result;
    uint8_t data[3];
    uint8_t check_code[2];
  } bytes;
  uint8_t array[sizeof(bytes)];
} laser_rcv_data;
#endif

RunningMedian filter = RunningMedian(FILTERVALUES);

void setup() {
  int countdownMS = Watchdog.enable(8000);
#if VERBOSE > 0
  Serial.begin(9600);
#endif
  //Start up software serial to communicate with the laser device
#if VERBOSE > 0
  Serial.println(F("Init software serial for laser"));
#endif
#if LASER_DEVICE == 1
  Laser.begin(19200);
#if VERBOSE > 0
  Serial.println(F("Success for HIREED device"));
#endif
#elif LASER_DEVICE == 2
  Laser.begin(38400);
  //Write some commands in struct
  laser_send_data.bytes.preamble = 0xAA;
  laser_send_data.bytes.command = 0x03;
#if VERBOSE > 0
  Serial.println(F("Success for HOLO device"));
#endif
#endif
  //Start up I²C and register interrupt routines
  Wire.begin(I2C_SLAVE_ADR);                // join i2c bus with address
  Wire.onRequest(requestEvent);             // register event
  Wire.onReceive(receiveEvent);             // register event
  pinMode(LED, OUTPUT);

  //Retrieve setup height from EEprom
  EEPROM.get(eeAddress, setupHeight);
#if VERBOSE > 0
  Serial.print(F("Getting setup height from EEPROM: "));
  Serial.print(setupHeight);
  Serial.println(F(" mm"));
#endif
  //Setup pin mode for tare pin
  pinMode(TAREPIN, INPUT_PULLUP);
}

void loop() {
  //Reset Watchdog
  Watchdog.reset();

  //Get tare distance and save to EEPROM and blink the LED long and 2 times short
  if (digitalRead(TAREPIN) == LOW) {
    digitalWrite(LED, HIGH);
    setupHeight = filter.getMedian();
    EEPROM.put(eeAddress, setupHeight);
#if VERBOSE > 0
    Serial.print(F("New tare value written to EEPROM: "));
    Serial.println(setupHeight);
#endif
    delay(1000);
    digitalWrite(LED, LOW);
    delay(300);
    digitalWrite(LED, HIGH);
    delay(300);
    digitalWrite(LED, LOW);
    delay(300);
    digitalWrite(LED, HIGH);
    delay(300);
    digitalWrite(LED, LOW);
  }

  //Timing for reading the distance and state of the laser device
  if (((millis() - LastMeasurement) > SCANNINGTIME) || (state == 2)) {
    LastMeasurement = millis();
    state = 0;
    state_trigger = 0;
#if LASER_DEVICE == 1
    HIREED_get_Distance();
#elif LASER_DEVICE == 2
    HOLO_get_distance();
#endif
    RcvTimeout = millis();
  }
  if (((millis() - LastMeasurement) > SCANNINGTIME / 2 && state_trigger == 0) || (state == 1)) {
    state_trigger = 1;
#if LASER_DEVICE == 1
    state = 0;
    HIREED_get_Status();
#elif LASER_DEVICE == 2
    if (initRunCtr == 0) {
      state = 2; //Since status is not available with the HOLO laser jump to the distance reading
    }
    Serial.println(F("No status message available when HOLO Laser is configured"));
#endif
  }

  //If debug mode is enabled allow routing messages through hardware serial
#if VERBOSE > 0
  if (Serial.available()) {           // If anything comes from the serial (USB) bus,
    Laser.write(Serial.read());       // read it and send it out to laser
  }
#endif

if ((millis() - RcvTimeout > TIMEOUT) && state == 0 && ErrMsg == 0){
  ErrMsg = 1;
  #if VERBOSE > 0
      Serial.println(F("Nothing received from Laser device. Check wiring"));
  #endif
}

  //Retrieve messages from the laser and parse them
  if (Laser.available()) {            // read answer from laser
    ErrMsg == 0;                      // Reset communication error
#if LASER_DEVICE == 1
    HIREED_read_Data();
#elif LASER_DEVICE == 2
    delay(100);                       // wait 100ms to be sure the whole string sent by the device is in the buffer
    HOLO_read_data();
#endif

  }
}
