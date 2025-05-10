#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "YourWiFiSSID";
const char* password = "YourWiFiPassword";

// Server connection details
const char* serverUrl = "http://your-server-ip:8000";  // Replace with your server IP/hostname
const int speakerId = 1;    // ID of the speaker/sender user
const int listenerId = 2;   // ID of the listener/receiver user (this device)
int lastSequenceId = 0;     // Track the last sequence ID we've processed

// Motor pin configuration
const uint8_t motorPins[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11};  // 10 output pins
const uint8_t NUM_MOTORS = sizeof(motorPins) / sizeof(motorPins[0]);

// Timing configuration
const unsigned long POLLING_INTERVAL_MS = 250;   // Poll server every 250ms
const unsigned long WIFI_RETRY_INTERVAL = 5000;  // Try to reconnect to WiFi every 5 seconds
const unsigned long RANDOM_PATTERN_INTERVAL = 2000; // Change random pattern every 2 seconds
unsigned long lastPollTime = 0;
unsigned long lastWiFiRetryTime = 0;
unsigned long lastRandomPatternTime = 0;

// Maximum number of sequences to process at once
const int MAX_SEQUENCES = 5;
// Maximum number of motors that can be active at once
const int MAX_ACTIVE_MOTORS = 4;

// Haptic sequence structure
struct HapticSequence {
  int sequenceId;
  int numMotors;
  int motorIds[MAX_ACTIVE_MOTORS];  // Which motors to activate (0-9)
  int durationMs;
  int restMs;
};

// Queue to store upcoming haptic sequences
HapticSequence sequenceQueue[MAX_SEQUENCES];
int queueSize = 0;
int currentSequenceIndex = 0;

// Current haptic state
bool isPlaying = false;
bool isActivationPhase = false;
unsigned long phaseStartTime = 0;

// Random pattern state
int randomSeed = 0;
bool isRandomMode = false;

// Buffer for storing HTTP response
const int MAX_RESPONSE_SIZE = 512;
char responseBuffer[MAX_RESPONSE_SIZE];

void setup() {
  Serial.begin(115200);
  
  // Initialize motor pins
  for (uint8_t i = 0; i < NUM_MOTORS; ++i) {
    pinMode(motorPins[i], OUTPUT);
    digitalWrite(motorPins[i], LOW);  // start off
  }
  
  // Initialize random seed with analog noise
  randomSeed = analogRead(A0);
  
  // Connect to WiFi
  connectToWiFi();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check WiFi connection status
  if (WiFi.status() != WL_CONNECTED) {
    // We're not connected to WiFi
    isRandomMode = true;
    
    // Try to reconnect periodically
    if (currentTime - lastWiFiRetryTime >= WIFI_RETRY_INTERVAL) {
      Serial.println("Attempting to reconnect to WiFi...");
      WiFi.reconnect();
      lastWiFiRetryTime = currentTime;
    }
  } else {
    // We have WiFi, switch to normal mode if we were in random mode
    if (isRandomMode) {
      Serial.println("WiFi connected! Switching to server mode.");
      isRandomMode = false;
      
      // Clear any ongoing random activations
      if (isPlaying && queueSize == 0) {
        isPlaying = false;
        allMotorsOff();
      }
    }
    
    // Check if it's time to poll for new sequences
    if (currentTime - lastPollTime >= POLLING_INTERVAL_MS) {
      pollServer();
      lastPollTime = currentTime;
    }
  }
  
  // If we're in random mode and have no queued sequences, generate random patterns
  if (isRandomMode && queueSize == 0 && !isPlaying) {
    if (currentTime - lastRandomPatternTime >= RANDOM_PATTERN_INTERVAL) {
      generateRandomPattern();
      lastRandomPatternTime = currentTime;
    }
  }
  
  // Process haptic sequences (both server-driven and random)
  processHapticSequences(currentTime);
}

void connectToWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  
  // Wait for connection with timeout
  int attemptCount = 0;
  while (WiFi.status() != WL_CONNECTED && attemptCount < 20) {
    delay(500);
    Serial.print(".");
    attemptCount++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("Connected to WiFi, IP address: ");
    Serial.println(WiFi.localIP());
    isRandomMode = false;
  } else {
    Serial.println();
    Serial.println("Failed to connect to WiFi. Operating in random pattern mode.");
    isRandomMode = true;
  }
}

void pollServer() {
  HTTPClient http;
  
  // Construct the URL with the speaker ID, listener ID, and last sequence ID
  String url = String(serverUrl) + "/haptic_csv/" + speakerId + "/" + 
               listenerId + "?last_sequence_id=" + lastSequenceId;
  
  http.begin(url);
  int httpResponseCode = http.GET();
  
  if (httpResponseCode == 200) {
    String response = http.getString();
    if (response.length() < MAX_RESPONSE_SIZE) {
      response.toCharArray(responseBuffer, MAX_RESPONSE_SIZE);
      parseCSVResponse(responseBuffer);
    } else {
      Serial.println("Response too large for buffer");
    }
  } else {
    Serial.print("Error on HTTP request. Code: ");
    Serial.println(httpResponseCode);
  }
  
  http.end();
}

// Parse a CSV value from the buffer, advancing the pointer
int parseCSVInt(char** ptr) {
  int value = atoi(*ptr);
  
  // Skip to the next delimiter or end
  while (**ptr && **ptr != ',' && **ptr != '\n') {
    (*ptr)++;
  }
  
  // Skip delimiter
  if (**ptr) {
    (*ptr)++;
  }
  
  return value;
}

void parseCSVResponse(char* response) {
  char* ptr = response;
  
  // Parse the header line: seq_counter,num_sequences
  int newLastSequenceId = parseCSVInt(&ptr);
  int numSequences = parseCSVInt(&ptr);
  
  // Update our last sequence ID
  if (newLastSequenceId > lastSequenceId) {
    lastSequenceId = newLastSequenceId;
  }
  
  if (numSequences == 0) {
    // No new sequences
    return;
  }
  
  Serial.print("Received ");
  Serial.print(numSequences);
  Serial.println(" new sequences");
  
  // Clear existing queue if we're not currently playing a sequence
  if (!isPlaying) {
    queueSize = 0;
    currentSequenceIndex = 0;
  }
  
  // Parse each sequence line
  for (int i = 0; i < numSequences && queueSize < MAX_SEQUENCES; i++) {
    if (!*ptr) {
      Serial.println("Unexpected end of data");
      break;
    }
    
    HapticSequence newSequence;
    
    // Parse: seq_id,num_motors,motor1,motor2,...,duration,rest
    newSequence.sequenceId = parseCSVInt(&ptr);
    newSequence.numMotors = parseCSVInt(&ptr);
    
    // Limit motors to our maximum
    if (newSequence.numMotors > MAX_ACTIVE_MOTORS) {
      newSequence.numMotors = MAX_ACTIVE_MOTORS;
    }
    
    // Parse motor IDs
    for (int j = 0; j < newSequence.numMotors; j++) {
      newSequence.motorIds[j] = parseCSVInt(&ptr);
    }
    
    // Parse duration and rest
    newSequence.durationMs = parseCSVInt(&ptr);
    newSequence.restMs = parseCSVInt(&ptr);
    
    // Skip to next line
    while (*ptr && *ptr != '\n') {
      ptr++;
    }
    if (*ptr == '\n') {
      ptr++;
    }
    
    // Add to queue
    sequenceQueue[queueSize++] = newSequence;
  }
}

// Generate a random but somewhat consistent pattern based on our seed
void generateRandomPattern() {
  // Increment the seed to get different but consistent patterns
  randomSeed = (randomSeed * 1103515245 + 12345) % 2147483647;
  
  // Clear the queue to start fresh
  queueSize = 0;
  
  // Create a new sequence
  HapticSequence newSequence;
  newSequence.sequenceId = randomSeed % 1000; // Just for tracking
  
  // Determine how many motors to activate (1-4)
  newSequence.numMotors = (randomSeed % MAX_ACTIVE_MOTORS) + 1;
  
  // Choose which motors to activate
  for (int i = 0; i < newSequence.numMotors; i++) {
    int nextRand = (randomSeed / (i+1)) % NUM_MOTORS;
    newSequence.motorIds[i] = nextRand;
    
    // Ensure no duplicates
    for (int j = 0; j < i; j++) {
      if (newSequence.motorIds[j] == newSequence.motorIds[i]) {
        // If duplicate, pick next available motor
        newSequence.motorIds[i] = (newSequence.motorIds[i] + 1) % NUM_MOTORS;
        j = -1; // Restart check
      }
    }
  }
  
  // Standard timing
  newSequence.durationMs = 300;
  newSequence.restMs = 150;
  
  // Add to queue
  sequenceQueue[queueSize++] = newSequence;
  
  Serial.print("Generated random pattern with motors: ");
  for (int i = 0; i < newSequence.numMotors; i++) {
    Serial.print(newSequence.motorIds[i]);
    if (i < newSequence.numMotors - 1) {
      Serial.print(", ");
    }
  }
  Serial.println();
}

void processHapticSequences(unsigned long currentTime) {
  // If we're not playing anything and the queue is empty, nothing to do
  if (!isPlaying && queueSize == 0) {
    return;
  }
  
  // If we're not playing but have sequences in queue, start playing
  if (!isPlaying && queueSize > 0) {
    startPlaying(currentTime);
    return;
  }
  
  // If we're playing, check if it's time to switch phases or sequences
  if (isPlaying) {
    unsigned long elapsedTime = currentTime - phaseStartTime;
    HapticSequence& currentSequence = sequenceQueue[currentSequenceIndex];
    
    if (isActivationPhase && elapsedTime >= currentSequence.durationMs) {
      // Activation phase complete, start rest phase
      allMotorsOff();
      isActivationPhase = false;
      phaseStartTime = currentTime;
    } 
    else if (!isActivationPhase && elapsedTime >= currentSequence.restMs) {
      // Rest phase complete, move to next sequence
      currentSequenceIndex++;
      
      if (currentSequenceIndex >= queueSize) {
        // All sequences complete
        isPlaying = false;
        queueSize = 0;
        currentSequenceIndex = 0;
        
        // If in random mode, immediately generate a new pattern
        if (isRandomMode) {
          // Add a small delay before the next pattern
          lastRandomPatternTime = currentTime;
        }
      } else {
        // Start next sequence
        startCurrentSequence(currentTime);
      }
    }
  }
}

void startPlaying(unsigned long currentTime) {
  isPlaying = true;
  currentSequenceIndex = 0;
  startCurrentSequence(currentTime);
}

void startCurrentSequence(unsigned long currentTime) {
  HapticSequence& sequence = sequenceQueue[currentSequenceIndex];
  
  // First, turn all motors off
  allMotorsOff();
  
  // Then activate motors from the current sequence
  for (int i = 0; i < sequence.numMotors; i++) {
    int motorId = sequence.motorIds[i];
    if (motorId >= 0 && motorId < NUM_MOTORS) {
      digitalWrite(motorPins[motorId], HIGH);
    }
  }
  
  isActivationPhase = true;
  phaseStartTime = currentTime;
  
  // Debug info
  Serial.print("Playing sequence ");
  Serial.print(sequence.sequenceId);
  Serial.print(": Motors ");
  for (int i = 0; i < sequence.numMotors; i++) {
    Serial.print(sequence.motorIds[i]);
    if (i < sequence.numMotors - 1) {
      Serial.print(",");
    }
  }
  Serial.println();
}

void allMotorsOff() {
  for (uint8_t i = 0; i < NUM_MOTORS; ++i) {
    digitalWrite(motorPins[i], LOW);
  }
}
