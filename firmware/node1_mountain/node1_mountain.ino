// Node 1: Mountain Landslide Monitoring Node
// Hardware: ESP32 + LoRa (SX1276/78) + Soil Moisture (Analog) + Vibration/Shock (Analog/Digital)
// Uses sandeepmistry/LoRa library for Arduino framework.

#include <SPI.h>
#include <LoRa.h>

// Configurable SPI Pins for ESP32-LoRa RFM95
#define SCK 5
#define MISO 19
#define MOSI 27
#define SS 18
#define RST 14
#define DIO0 26

#define BAND 915E6 // LoRa Frequency Band (e.g. 868E6 for EU, 915E6 for US/Asia)

// Configurable Sensor Pins
#define SOIL_PIN 34       // Soil Moisture Sensor Analog Pin
#define VIBRATION_PIN 35  // Vibration / Seismic Sensor Pin

unsigned long packet_id = 0;
const int txInterval = 5000; // Transmit every 5 seconds
unsigned long lastTxTime = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("D-SHIELD Node 1 [Mountain] - Booting Up...");

  // Setup custom SPI pins for LoRa module
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(BAND)) {
    Serial.println("Error: LoRa module initialization failed! Check wiring.");
    while (1);
  }
  
  // Set custom sync word (0xD5 for D-SHIELD networks) to isolate communication
  LoRa.setSyncWord(0xD5);
  
  pinMode(SOIL_PIN, INPUT);
  pinMode(VIBRATION_PIN, INPUT);
  
  Serial.println("D-SHIELD Node 1 [Mountain] - Online (LoRa Active).");
}

void loop() {
  if (millis() - lastTxTime > txInterval) {
    lastTxTime = millis();
    
    // Read and calibrate soil moisture (0-100%)
    int rawSoil = analogRead(SOIL_PIN);
    // Note: Calibrated maps where 4095 is dry and 1100 is fully saturated in water
    float soilMoisturePercent = map(rawSoil, 4095, 1100, 0, 100);
    if (soilMoisturePercent < 0) soilMoisturePercent = 0.0;
    if (soilMoisturePercent > 100) soilMoisturePercent = 100.0;
    
    // Read and scale vibration readings to representative g-forces (0.0 to 10.0g)
    // Runs multiple high speed reads to capture vibration peaks
    float maxVibRaw = 0.0;
    for (int i = 0; i < 50; i++) {
      float readVal = analogRead(VIBRATION_PIN);
      if (readVal > maxVibRaw) {
        maxVibRaw = readVal;
      }
      delayMicroseconds(500);
    }
    // Scale 0-4095 analog read to 0.0 - 10.0g representative vibration
    float vibrationG = (maxVibRaw / 4095.0) * 10.0;

    // Construct lightweight LoRa Packet payload
    // Format: NODE1,packet_id,soil_moisture,vibration
    String payload = "NODE1," + String(packet_id) + "," + String(soilMoisturePercent, 1) + "," + String(vibrationG, 2);
    
    Serial.print("D-SHIELD Tx Packet: ");
    Serial.println(payload);
    
    // Send packet via radio
    LoRa.beginPacket();
    LoRa.print(payload);
    LoRa.endPacket();
    
    packet_id++;
  }
}
