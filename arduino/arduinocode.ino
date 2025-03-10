#include <WiFi.h>
#include <WiFiUdp.h>
#include <Ticker.h>

int status = WL_IDLE_STATUS;

// Please enter your sensitive data in the Secret tab/arduino_secrets.h
char ssid[] = "WIFINAME"; // your network SSID (name)
char pass[] = "WIFIPASSWORD"; // your network password (use for WPA, or use as key for WEP)
int USER_ID = 21;
unsigned int localPort = 2390; // local port to listen on
unsigned int remotePort = 8081
; // remote port to send data to
WiFiUDP Udp;
IPAddress remoteIp; // Define the remote IP address (this should be set to the server's IP)

void setup() {
  remoteIp.fromString("XX.XX.XX.XX"); // Change the IP address here to UDP server
  Serial.begin(115200);

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    while (true);
  }

  String fv = WiFi.firmwareVersion();
  if (fv < WIFI_FIRMWARE_LATEST_VERSION) {
    Serial.println("Please upgrade the firmware");
  }

  while (status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    Serial.print("WiFi status: ");
    Serial.println(WiFi.status());
    delay(10000);
  }
  Serial.println("Connected to WiFi");
  printWifiStatus();

  Udp.begin(localPort);
}


void loop() {
  // Read sensor values
  int sensorValues[6];
  for (int i = 0; i < 6; i++) {
    sensorValues[i] = analogRead(i);
  }

  // Get the current timestamp
  unsigned long timestamp = millis();

  // Create a character array to hold the data
  char data[100];

  // Format the data as a comma-separated string and get the length
  int length = sprintf(data, "%d,%lu,%d,%d,%d,%d,0", USER_ID, timestamp, sensorValues[0], sensorValues[1], sensorValues[2], sensorValues[3]);

  // Send UDP packet
  Udp.beginPacket(remoteIp, remotePort);
  Udp.write(data, length);
  Udp.endPacket();

  // Print sent data to serial monitor
  Serial.println(data);

  // Wait before sending the next packet
  delay(10);
}

void printWifiStatus() {
  // Print the SSID of the network you're attached to:
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  // Print your board's IP address:
  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);

  // Print the received signal strength:
  long rssi = WiFi.RSSI();
  Serial.print("signal strength (RSSI):");
  Serial.print(rssi);
  Serial.println(" dBm");
}