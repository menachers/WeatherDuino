// --------------------------------------------------------------------------------------
//   Snow height measurement system - Version: 4.2
//           Start of user configurable options 
// --------------------------------------------------------------------------------------

// --------------------------------------------------------------------------------------
//   Used laser ranging device
// --------------------------------------------------------------------------------------
#define LASER_DEVICE 2  // 1 for HIREED laser, 2 for HOLO laser

// --------------------------------------------------------------------------------------
//   Scanning frequency in ms
// --------------------------------------------------------------------------------------
#define SCANNINGTIME 300000

// --------------------------------------------------------------------------------------------
//   Set tilt angle of ranging device in degree to correct the measured snow height via cosine
// --------------------------------------------------------------------------------------------
#define ALPHA 10

// --------------------------------------------------------------------------------------------
//   Define temperature sensor which should be emulated
// --------------------------------------------------------------------------------------------
#define SENSOR 1    //0 for HTU, 1 for SHT3X

// --------------------------------------------------------------------------------------------
//   Define I²C slave adress for the emulated temperature sensor
// --------------------------------------------------------------------------------------------
#define I2C_SLAVE_ADR 0x44

// --------------------------------------------------------------------------------------------
// Define number of running median filter samples
// The number of filter messages times the scanning time should not be more than half an hour to minimize the delay
// --------------------------------------------------------------------------------------------
#define FILTERVALUES 10

// --------------------------------------------------------------------------------------------
// Unit for snow height transmission
// Please think of possible limitations when transmitting as extra humidity via davis protocol
// Be careful that the snow height has to be in a range between 0 and 99.9 - values below and above will be cut.
// If you want to export it via davis protocol to your weather software you might chose cm, to get a resolution of 1cm
// after transmitting it to you software.
// If you use dm you have a resolution of 1dm (10cm) after transmitting it via Davis protocoll.
// --------------------------------------------------------------------------------------------
#define SNOWUNIT 1    // 1 for cm,  2 for dm, 3 for inch


// --------------------------------------------------------------------------------------------
// Enable debugging messages via serial monitor
// --------------------------------------------------------------------------------------------
#define VERBOSE 2    // 2 all messages, 1 overview, 0 all messages off
