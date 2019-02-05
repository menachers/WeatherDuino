void Com_Transmit() {
  // --- Write all signals on COM 3
  byte* VarPtr;
  uint8_t TransmitCRC = 0;
  uint16_t SumBytes = 0;

  //Serial.println(millis());

  //Write rx internal variables
  uint32_t timestamp = now();
  VarPtr = (byte*) &timestamp;
  Serial3.write(VarPtr, sizeof(timestamp));
  //Calculate checksum
  for (uint8_t i = 0; i < (sizeof(timestamp)); i++) {
    TransmitCRC = TransmitCRC ^ (*VarPtr);
    /*Serial.print("Payload Byte: ");
      Serial.println(*VarPtr, HEX);
      Serial.print("Prüfsumme: ");
      Serial.println(TransmitCRC, HEX);*/
    VarPtr++;
    SumBytes ++;
  }

  VarPtr = (byte*) &Output_T_Int;
  Serial3.write(VarPtr, sizeof(Output_T_Int));
  //Calculate checksum
  for (uint8_t i = 0; i < (sizeof(Output_T_Int)); i++) {
    TransmitCRC = TransmitCRC ^ (*VarPtr);
    VarPtr++;
    SumBytes ++;
  }

  VarPtr = (byte*) &Output_H_Int;
  Serial3.write(VarPtr, sizeof(Output_H_Int));
  //Calculate checksum
  for (uint8_t i = 0; i < (sizeof(Output_H_Int)); i++) {
    TransmitCRC = TransmitCRC ^ (*VarPtr);
    VarPtr++;
    SumBytes ++;
  }

  VarPtr = (byte*) &pressure_mB;
  Serial3.write(VarPtr, sizeof(pressure_mB));
  //Calculate checksum
  for (uint8_t i = 0; i < (sizeof(pressure_mB)); i++) {
    TransmitCRC = TransmitCRC ^ (*VarPtr);
    VarPtr++;
    SumBytes ++;
  }
  
  for (uint8_t u = 0; u < 4; u++){
	VarPtr = (byte*) &avg_RX_PacketsPerHour_TXunit[u];
    Serial3.write(VarPtr, sizeof(avg_RX_PacketsPerHour_TXunit[u]));
    //Calculate checksum
    for (uint8_t i = 0; i < (sizeof(avg_RX_PacketsPerHour_TXunit[u])); i++) {
      TransmitCRC = TransmitCRC ^ (*VarPtr);
      VarPtr++;
      SumBytes ++;
    }
  }
  //Write variables of TX Modules and values of rain sensor collector multipliers
  for (uint8_t u = 0; u < 4; u++) {
    VarPtr = (byte*) &TX_Unit[u];
    Serial3.write(VarPtr, sizeof(TX_Unit[u]));
    //Calculate checksum
    for (uint8_t i = 0; i < (sizeof(TX_Unit[u])); i++) {
      TransmitCRC = TransmitCRC ^ (*VarPtr);
      VarPtr++;
      SumBytes ++;
    }

    VarPtr = (byte*) &COLLECTOR_TYPE[u];
    Serial3.write(VarPtr, sizeof(COLLECTOR_TYPE[u]));
    //Calculate checksum
    for (uint8_t i = 0; i < (sizeof(COLLECTOR_TYPE[u])); i++) {
      TransmitCRC = TransmitCRC ^ (*VarPtr);
      VarPtr++;
      SumBytes ++;
    }
  }
  
  //Write variables of Soil/Leaf temperature and wetness
  for (uint8_t u = 0; u < 2; u++) {
    for (uint8_t i = 0; i < 4; i++) {
      VarPtr = (byte*) &Soil_Data[i][u];
      Serial3.write(VarPtr, sizeof(Soil_Data[i][u]));
      //Calculate checksum
      for (uint8_t i = 0; i < (sizeof(Soil_Data[i][u])); i++) {
        TransmitCRC = TransmitCRC ^ (*VarPtr);
        VarPtr++;
        SumBytes ++;
      }
    }
  }
  for (uint8_t u = 0; u < 2; u++) {
    for (uint8_t i = 0; i < 4; i++) {
      VarPtr = (byte*) &Leaf_Data[i][u];
      Serial3.write(VarPtr, sizeof(Leaf_Data[i][u]));
      //Calculate checksum
      for (uint8_t i = 0; i < (sizeof(Leaf_Data[i][u])); i++) {
        TransmitCRC = TransmitCRC ^ (*VarPtr);
        VarPtr++;
        SumBytes ++;
      }
    }
  }
  //Write variables of AQM
  VarPtr = (byte*) &AQI_Monitor;
  Serial3.write(VarPtr, sizeof(AQI_Monitor));
  //Calculate checksum
  for (uint8_t i = 0; i < (sizeof(AQI_Monitor)); i++) {
    TransmitCRC = TransmitCRC ^ (*VarPtr);
    VarPtr++;
    SumBytes ++;
  }

  //Write variables of Wifi WDs
  for (uint8_t u = 0; u < 4; u++) {
    for (uint8_t i = 0; i < 2; i++) {
      VarPtr = (byte*) &WiFi_THdata[u][i];
      Serial3.write(VarPtr, sizeof(WiFi_THdata[u][i]));
      //Calculate checksum
      for (uint8_t i = 0; i < (sizeof(WiFi_THdata[u][i])); i++) {
        TransmitCRC = TransmitCRC ^ (*VarPtr);
        VarPtr++;
        SumBytes ++;
      }
    }
  }


  //Write sum of all sent bytes
  VarPtr = (byte*) &SumBytes;
  Serial3.write(VarPtr, sizeof(SumBytes));


  //Write CRC
  Serial3.write(TransmitCRC);
  //Write end bytes
  Serial3.write(0xAB);
  Serial3.write(0xCD);

  //Serial.println(millis());
  //Serial.println("Serial 3 written");
}
