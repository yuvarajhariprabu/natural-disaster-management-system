// Node 2: River Flood Monitoring Node
// Hardware: ESP32 + LoRa (SX1276/78) + HC-SR04 Ultrasonic (Trigger/Echo) + BMP280 (I2C)
// Uses sandeepmistry/LoRa and Adafruit BMP280 library.

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>

// Configurable SPI Pins for ESP32-LoRa RFM95
#define SCK 5
#define MISO 19
#define MOSI 27
#define SS 18
#define RST 14
#define DIO0 26

#define BAND 915E6

// HC-SR04 Ultrasonic Pins
#define TRIG_PIN 32
#define ECHO_PIN 33

// I2C pins for BMP280
#define I2C_SDA 21
#define I2C_SCL 22

// Configurable Physical Installation Constants
const float MOUNTING_HEIGHT = 5.0; // In meters (distance from sensor face to dry river bed)

Adafruit_BMP280 bmp; // I2C sensor
unsigned long packet_id = 0;
const int txInterval = 5000; // Transmit every 5 seconds
unsigned long lastTxTime = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("D-SHIELD Node 2 [River] - Booting Up...");

  // Setup HC-SR04 pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Setup I2C & BMP280
  Wire.begin(I2C_SDA, I2C_SCL);
  if (!bmp.begin(0x76)) { // 0x76 or 0x77 I2C address
    Serial.println("Warning: BMP280 sensor not found! Check wiring. System will send default temp/press.");
  }

  // Setup custom SPI pins for LoRa module
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(BAND)) {
    Serial.println("Error: LoRa module initialization failed!");
    while (1);
  }
  
  LoRa.setSyncWord(0xD5);
  
  Serial.println("D-SHIELD Node 2 [River] - Online (LoRa Active).");
}

void loop() {
  if (millis() - lastTxTime > txInterval) {
    lastTxTime = millis();
    
    // 1. Read Ultrasonic distance in meters
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    
    long duration = pulseIn(ECHO_PIN, HIGH);
    // Speed of sound: 340 m/s or 0.034 cm/us. Total round-trip distance is duration * 0.0343 / 2.
    // Convert cm to meters: distance = duration * 0.0343 / 200.0
    float distanceM = (duration * 0.0343) / 200.0;
    
    // Prevent bad readings
    if (distanceM <= 0.0 || distanceM > 10.0) {
      distanceM = MOUNTING_HEIGHT; // Default to dry if sensor times out
    }
    
    // Water level calculation
    float waterLevel = MOUNTING_HEIGHT - distanceM;
    if (waterLevel < 0.0) waterLevel = 0.0; // avoid negative values
    
    // 2. Read BMP280 weather metrics (defaults if sensor absent)
    float temp = 20.0;
    float press = 1013.25;
    
    // bmp.begin returns true if initialized
    if (bmp.getStatus() != 0xFF) {
      temp = bmp.readTemperature();
      press = bmp.readPressure() / 100.0; // convert Pa to hPa
    }

    // Construct lightweight LoRa Packet payload
    // Format: NODE2,packet_id,water_level,temperature,pressure
    String payload = "NODE2," + String(packet_id) + "," + String(waterLevel, 2) + "," + String(temp, 1) + "," + String(press, 2);
    
    Serial.print("D-SHIELD Tx Packet: ");
    Serial.println(payload);
    
    // Send packet via radio
    LoRa.beginPacket();
    LoRa.print(payload);
    LoRa.endPacket();
    
    packet_id++;
  }
}
