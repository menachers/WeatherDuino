#if LASER_DEVICE == 1
//Functions for HIREED laser
void HIREED_get_Distance (void) {
  Laser.print("D");
#if VERBOSE > 1
  Serial.println("D sent to laser ranging device");
#endif
}

void HIREED_get_Status (void) {
  Laser.print("S");
#if VERBOSE > 1
  Serial.println("S sent to laser ranging device");
#endif
}

void HIREED_read_Data (void) {
  char s = Laser.read();
  if (s != '\n') {
    inputBuffer[a] = s;
    if (isdigit(s) == 0) {
      digitPtr = a + 1;
    }
    a++;
  }
  else {
    inputBuffer[a] = s;
    inputBuffer[a + 1] = '\0';
    a = 0;
    //Serial.print(inputBuffer);
    buf = ((char*)inputBuffer);
#if VERBOSE > 1
    Serial.print(buf);
#endif
    //Test if a distance result is available
    if (buf.startsWith("D:")) {
      resultString = buf.substring(3);
      //Test if there is an error code
      if (buf.substring(2).startsWith("Er")) {

#if VERBOSE > 0
        Serial.println("Error detected");
        Serial.println(buf.substring(5).toInt());
#endif
      }
      //If there is no error parse the result value
      else {
        uint8_t ind = resultString.indexOf(".");
        //Purge decimal seperator
        resultString.remove(ind, ind);
        distance = resultString.toInt();
        //Do tilt correction of measured distance
        //cos (alpha) = real distance / measured distance
        distance = (int)(cos((PI / 180) * ALPHA) * distance);
        //Put the distance value in filter array
        filter.add((distance));
        //Handle init run to fill array on start
        if (initRunCtr < FILTERVALUES) {
          state = 2;
          initRunCtr++;
#if VERBOSE > 0
          Serial.print("Filling filter: ");
          Serial.print (initRunCtr);
          Serial.print (" von ");
          Serial.println(FILTERVALUES);
#endif
        }
        else {
          state = 3;
        }

#if VERBOSE > 0
        Serial.print("Distance read succesfully: ");
        Serial.println(distance);
#endif
        /*
          #if VERBOSE > 0
          Serial.println(distance);
          #endif
        */
      }
    }
    else if (buf.startsWith("S:")) {
#if VERBOSE > 0
      Serial.println("state information detected");
#endif
      temperature = (int) (buf.substring(3).toFloat() * 10);
      voltage = (int) (buf.substring(10).toFloat() * 10);
      state = 2;
    }
  }
}
#endif

#if LASER_DEVICE == 2
void HOLO_get_distance(void) {
  laser_send_data.bytes.check_code[0] = (uint8_t)(laser_send_data.bytes.preamble + laser_send_data.bytes.command + laser_send_data.bytes.data[0] + laser_send_data.bytes.data[1] + laser_send_data.bytes.data[2]) << 8;
  laser_send_data.bytes.check_code[1] = (uint8_t)(laser_send_data.bytes.preamble + laser_send_data.bytes.command + laser_send_data.bytes.data[0] + laser_send_data.bytes.data[1] + laser_send_data.bytes.data[2]);

  Laser.write(laser_send_data.array, sizeof(laser_send_data.array));
}

void HOLO_read_data(void) {
  uint16_t checksum = 0;
  Laser.readBytes(laser_rcv_data.array, sizeof(laser_rcv_data.array));
  for (uint8_t i = 0; i < sizeof(laser_rcv_data.array) - 2; i++) {
    checksum = checksum + laser_rcv_data.array[i];
  }

#if VERBOSE > 1
  Serial.println(checksum, HEX);
  Serial.println(laser_rcv_data.bytes.check_code[0], HEX);
  Serial.println(laser_rcv_data.bytes.check_code[1], HEX);
#endif

  if ((laser_rcv_data.bytes.command == 0x03) && (laser_rcv_data.bytes.result == 0x06) && (checksum == (laser_rcv_data.bytes.check_code[0] << 8 | laser_rcv_data.bytes.check_code[1]))) {
    distance = (int16_t)((laser_rcv_data.bytes.data[0] << 16) | (laser_rcv_data.bytes.data[1] << 8) | laser_rcv_data.bytes.data[2]);
    //Do tilt correction of measured distance
    //cos (alpha) = real distance / measured distance
    distance = (int)(cos((PI / 180) * ALPHA) * distance);
    //Put the distance value in filter array
    filter.add((distance));

    //Handle init run to fill array on start
    if (initRunCtr < FILTERVALUES) {
      state = 2;
      initRunCtr++;
#if VERBOSE > 0
      Serial.print("Filling filter: ");
      Serial.print (initRunCtr);
      Serial.print (" von ");
      Serial.println(FILTERVALUES);
#endif
    }
    else {
      state = 3;
    }

  }
  else {
    distance = -1;
  }
#if VERBOSE > 0
  Serial.print("Distance is ");
  Serial.print (distance);
  Serial.println(" mm");
#endif
}

#endif

//Interrupt based handling of I2C recieve event
void receiveEvent(int howMany) {
  digitalWrite(LED, HIGH);
  int x = Wire.read();    // receive byte as an integer
#if VERBOSE > 1
  Serial.print("I2C input received: ");
  Serial.println(x, HEX); // print the integer
#endif
  if (x == 0xE7) {        //Case init
    i2cRequest = 1;
  }
  else if (x == 0xF3) {   //Case read temp
    i2cRequest = 2;
  }
  else if (x == 0xF5) {   //Case read hum
    i2cRequest = 3;
  }
  else if (x == 0xFE) {   //Case reset
    i2cRequest = 4;
  }
  digitalWrite(LED, LOW);
}

//Interrupt based answer to I2C request based on the last reception
void requestEvent() {
  digitalWrite(LED, HIGH);
#if VERBOSE > 1
  Serial.println("I2C request received");
#endif
  if (i2cRequest == 1) {        //Handle if init was requested
    Wire.write(0x02);
  }
  else if (i2cRequest == 2 && state == 3) {   //Handle if temperature was requested
	
	//Check the variable to be in the allowed range
	if (temperature > 999) {
		temperature = 999;
	}
	else if (temperature < -400){
		temperature = 400;
	}
	
    float ttmp = temperature;
    ttmp /= 10;   //Convert to °C
    ttmp += 46.85;
    ttmp *= 65536;
    ttmp /= 175.72;


    uint16_t sendttmp = (uint16_t) ttmp;
    /*
      Serial.println (sendttmp, HEX);
      Serial.println((uint8_t) (sendttmp  >> 8), HEX);
      Serial.println((uint8_t) (sendttmp), HEX);
    */
    Wire.write((uint8_t) (sendttmp >> 8));
    Wire.write((uint8_t) (sendttmp));
    Wire.write(gen_crc(sendttmp)); //fills crc
#if VERBOSE > 0
    Serial.print("Temperature sent via I2C: ");
    Serial.println(temperature);
#endif
#if VERBOSE > 1
    Serial.print("Temperature raw sent via I2C: ");
    Serial.println(sendttmp);
#endif
  }
  else if (i2cRequest == 3 && state == 3) {   //Handle if temperature was requested
    float dtmp = setupHeight - filter.getMedian();

    //Convert corresponding to actual snow unit
#if SNOWUNIT == 1
    dtmp /= 10;
#elif SNOWUNIT == 2
    dtmp /= 100;
#elif SNOWUNIT == 3
    dtmp /= 25.4
#endif

//Check the variable to be in the allowed range
	if (dtmp > 99.9) {
		dtmp = 99.9;
	}
	else if (dtmp < -0.1){
		dtmp = -0.1;
	}

    dtmp += 6;
    dtmp *= 65536;
    dtmp /= 125;
    //dtmp = round(dtmp);
    uint16_t senddtmp = (uint16_t) dtmp;
    /*
      Serial.println (senddtmp, HEX);
      Serial.println((uint8_t) (senddtmp  >> 8), HEX);
      Serial.println((uint8_t) (senddtmp), HEX);
    */
    Wire.write((uint8_t) (senddtmp >> 8));
    Wire.write((uint8_t) (senddtmp));
    Wire.write(gen_crc(senddtmp)); //fills crc
#if VERBOSE > 0
    Serial.print("Snow heigt sent via I2C: ");
    Serial.print(setupHeight - filter.getMedian());
#if SNOWUNIT == 1
    Serial.println(" mm");
#elif SNOWUNIT == 2
    Serial.println(" dm");
#elif SNOWUNIT == 3
    Serial.println(" in");
#endif
#endif
#if VERBOSE > 1
    Serial.print("Distance raw sent via I2C: ");
    Serial.println(senddtmp);
#endif
    digitalWrite(LED, LOW);
  }
}


//Give this function the 2 byte message (measurement) generate the check sum of HTU21
//From: http://www.nongnu.org/avr-libc/user-manual/group__util__crc.html
//POLYNOMIAL = 0x0131 = x^8 + x^5 + x^4 + 1 : http://en.wikipedia.org/wiki/Computation_of_cyclic_redundancy_checks
#define SHIFTED_DIVISOR 0x988000 //This is the 0x0131 polynomial shifted to farthest left of three bytes

byte gen_crc(uint16_t message_from_sensor)
{
  //Test cases from datasheet:
  //message = 0xDC, checkvalue is 0x79
  //message = 0x683A, checkvalue is 0x7C
  //message = 0x4E85, checkvalue is 0x6B
  uint8_t check_value_from_sensor = 0x00;

  uint32_t remainder = (uint32_t)message_from_sensor << 8; //Pad with 8 bits because we have to add in the check value
  remainder |= check_value_from_sensor; //Add on the check value

  uint32_t divsor = (uint32_t)SHIFTED_DIVISOR;

  for (int i = 0 ; i < 16 ; i++) //Operate on only 16 positions of max 24. The remaining 8 are our remainder and should be zero when we're done.
  {
    //Serial.print("remainder: ");
    //Serial.println(remainder, BIN);
    //Serial.print("divsor:    ");
    //Serial.println(divsor, BIN);
    //Serial.println();

    if ( remainder & (uint32_t)1 << (23 - i) ) //Check if there is a one in the left position
      remainder ^= divsor;

    divsor >>= 1; //Rotate the divsor max 16 times so that we have 8 bits left of a remainder
  }

  return (byte)remainder;
}
