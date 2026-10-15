// Node 3: Rain Monitoring & LoRa Aggregator Node
// Hardware: ESP32 + LoRa (SX1276/78) + Rain Sensor (Analog)
// Receives Node 1/2 packets, combines with local rain data, and streams over USB Serial.

#include <SPI.h>
#include <LoRa.h>

// Configurable SPI Pins for ESP32-LoRa RFM95
#define SCK 5
#define MISO 19
#define MOSI 27
#define SS 18
#define RST 14
#define DIO0 26

#define BAND 915E6

// Rain Sensor Analog Pin
#define RAIN_PIN 36

unsigned long packet_id = 0;
const int txInterval = 5000; // Local rain transmission every 5 seconds
unsigned long lastTxTime = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("D-SHIELD Node 3 [Aggregator] - Booting Up...");

  // Setup custom SPI pins for LoRa module
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(BAND)) {
    Serial.println("Error: LoRa module initialization failed!");
    while (1);
  }
  
  LoRa.setSyncWord(0xD5);
  
  pinMode(RAIN_PIN, INPUT);
  
  Serial.println("D-SHIELD Node 3 [Aggregator] - Active. Awaiting Node 1 & Node 2 LoRa transmission...");
}

void loop() {
  // 1. Listen for incoming LoRa Packets
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incomingStr = "";
    while (LoRa.available()) {
      incomingStr += (char)LoRa.read();
    }
    
    // Capture LoRa Packet quality indicators
    float rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();
    
    // Append radio stats to the packet to forward to Gateway
    // Packet from Node 1 is formatted: NODE1,packet_id,soil_moisture,vibration
    // Packet from Node 2 is formatted: NODE2,packet_id,water_level,temperature,pressure
    // We forward as: <payload>,rssi,snr
    String forwardedPayload = incomingStr + "," + String(rssi, 1) + "," + String(snr, 1);
    
    // Stream directly to the PC Gateway via USB/Serial connection
    Serial.println(forwardedPayload);
  }

  // 2. Read local rain sensor and print to Serial
  if (millis() - lastTxTime > txInterval) {
    lastTxTime = millis();
    
    int rawRain = analogRead(RAIN_PIN);
    // Note: Rain sensor reading mappings where 4095 is dry, and 1200 is heavy rain
    float rainRateMM = map(rawRain, 4095, 1200, 0, 100);
    if (rainRateMM < 0.0) rainRateMM = 0.0;
    if (rainRateMM > 100.0) rainRateMM = 100.0;
    
    // Construct local aggregator packet (sent directly over USB serial)
    // Format: NODE3,packet_id,rainfall,rssi,snr
    // Since it's direct USB connected to gateway, RSSI/SNR are hardcoded to strong indicators
    String localPayload = "NODE3," + String(packet_id) + "," + String(rainRateMM, 1) + ",-45.0,12.0";
    
    Serial.println(localPayload);
    packet_id++;
  }
}
