/*
 * Context-Aware Predictive Maintenance - ESP32 edge node
 *
 * Every 2 s: sample vibration / temperature / current, classify locally
 * (Normal / Warning / Critical), drive LCD + LEDs + buzzer, and publish a JSON
 * payload to MQTT. Local alerting never depends on Wi-Fi or the broker.
 *
 * Boards   : ESP32-WROOM-32 (Arduino-ESP32 core 2.x or 3.x)
 * Libraries: PubSubClient, LiquidCrystal_I2C   (install via Library Manager)
 *
 * Pin map and thresholds follow Tables 3 and 4 of the project report.
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <math.h>
#include "config.h"

// ---------------------------------------------------------------- pins
constexpr uint8_t PIN_VIBRATION = 34;  // SW420 digital out (input-only pin)
constexpr uint8_t PIN_TEMP      = 35;  // LM35 analog out   (input-only pin)
constexpr uint8_t PIN_CURRENT   = 32;  // ACS712 out via 10k/20k divider
constexpr uint8_t PIN_LED_RED   = 25;
constexpr uint8_t PIN_LED_GREEN = 26;
constexpr uint8_t PIN_LED_YELLOW= 27;
constexpr uint8_t PIN_BUZZER    = 33;
// I2C LCD: SDA = GPIO21, SCL = GPIO22 (ESP32 defaults)

// ---------------------------------------------------------- thresholds
// Fault = value strictly ABOVE the limit. Recalibrate per motor nameplate.
constexpr float VIB_WARN = 3,    VIB_CRIT = 7;      // pulses per 2 s window
constexpr float TMP_WARN = 55.0, TMP_CRIT = 70.0;   // deg C
constexpr float CUR_WARN = 3.0,  CUR_CRIT = 4.5;    // A

// ------------------------------------------------------------- timing
constexpr uint32_t SAMPLE_MS         = 2000;
constexpr uint32_t WIFI_RETRY_MS     = 5000;
constexpr uint32_t MQTT_RETRY_MS     = 5000;
constexpr uint32_t CURRENT_WINDOW_MS = 200;   // 10 mains cycles at 50 Hz

// --------------------------------------------------- ACS712 + divider
constexpr float ACS_SENSITIVITY_V_PER_A = 0.185f;          // 5 A variant
constexpr float DIVIDER_RATIO           = 20.0f / (10.0f + 20.0f);
constexpr int   CAL_SAMPLES             = 100;

LiquidCrystal_I2C lcd(0x27, 16, 2);            // change to 0x3F if blank
WiFiClientSecure  net;
PubSubClient      mqtt(net);

volatile uint16_t vibPulses = 0;
float    currentOffsetV = 2.5f * DIVIDER_RATIO; // refined by calibration
float    lastValidTemp  = 25.0f;
uint32_t lastSample = 0, lastWifiTry = 0, lastMqttTry = 0;

void IRAM_ATTR onVibration() { vibPulses++; }

// ---------------------------------------------------------- sensing
float readTemperatureC() {
  // LM35: 10 mV / deg C. Average 16 samples to tame ADC noise.
  uint32_t raw = 0, mv = 0;
  for (int i = 0; i < 16; i++) { raw += analogRead(PIN_TEMP); mv += analogReadMilliVolts(PIN_TEMP); }
  raw /= 16; mv /= 16;
  // A floating / disconnected input pins near full scale and would show ~150 deg C.
  // Reject it and hold the last valid value instead of raising a false alarm.
  if (raw >= 4090 || raw == 0) return lastValidTemp;
  lastValidTemp = mv / 10.0f;
  return lastValidTemp;
}

float readCurrentA() {
  // The motor line is AC, so measure RMS of the sensor's deviation from its
  // zero-current offset over a whole number of mains cycles.
  double sumSq = 0; uint32_t n = 0, t0 = millis();
  while (millis() - t0 < CURRENT_WINDOW_MS) {
    float v = analogReadMilliVolts(PIN_CURRENT) / 1000.0f;
    float d = (v - currentOffsetV) / DIVIDER_RATIO;   // back to sensor-side volts
    sumSq += (double)d * d; n++;
  }
  float amps = sqrt(sumSq / max<uint32_t>(n, 1)) / ACS_SENSITIVITY_V_PER_A;
  return amps < 0.05f ? 0.0f : amps;                  // squash noise floor
}

void calibrateCurrentOffset() {
  // Run at boot with the motor OFF / no load current flowing.
  double sum = 0;
  for (int i = 0; i < CAL_SAMPLES; i++) { sum += analogReadMilliVolts(PIN_CURRENT) / 1000.0f; delay(5); }
  currentOffsetV = sum / CAL_SAMPLES;
}

// ---------------------------------------------------- classification
enum State { NORMAL, WARNING, CRITICAL };
const char* STATE_NAME[] = {"Normal", "Warning", "Critical"};

State classify(float vib, float tmp, float cur) {
  if (vib > VIB_CRIT || tmp > TMP_CRIT || cur > CUR_CRIT) return CRITICAL;
  if (vib > VIB_WARN || tmp > TMP_WARN || cur > CUR_WARN) return WARNING;
  return NORMAL;
}

void driveOutputs(State s) {
  digitalWrite(PIN_LED_GREEN,  s == NORMAL);
  digitalWrite(PIN_LED_YELLOW, s == WARNING);
  digitalWrite(PIN_LED_RED,    s == CRITICAL);
  digitalWrite(PIN_BUZZER,     s == CRITICAL);    // audible alert only when Critical
}

void showLcd(float tmp, float cur, uint16_t vib, State s) {
  char l1[17], l2[17];
  snprintf(l1, sizeof l1, "T:%.1fC I:%.1fA", tmp, cur);
  snprintf(l2, sizeof l2, "Vib:%u %s", vib, STATE_NAME[s]);
  lcd.setCursor(0, 0); lcd.print(l1); for (int i = strlen(l1); i < 16; i++) lcd.print(' ');
  lcd.setCursor(0, 1); lcd.print(l2); for (int i = strlen(l2); i < 16; i++) lcd.print(' ');
}

// ------------------------------------------------------ connectivity
// Non-blocking: if the network is down the sampling loop keeps running.
void maintainConnectivity() {
  uint32_t now = millis();
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifiTry >= WIFI_RETRY_MS) { lastWifiTry = now; WiFi.disconnect(); WiFi.begin(WIFI_SSID, WIFI_PASSWORD); }
    return;
  }
  if (!mqtt.connected() && now - lastMqttTry >= MQTT_RETRY_MS) {
    lastMqttTry = now;
    String id = "esp32-motor-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    mqtt.connect(id.c_str(), MQTT_USER, MQTT_PASSWORD);
  }
}

void publishReading(uint16_t vib, float tmp, float cur, State s) {
  if (!mqtt.connected()) return;
  char buf[160];
  // ts_ms (uptime) lets the dashboard measure end-to-end latency.
  snprintf(buf, sizeof buf,
           "{\"vibration\":%u,\"temperature\":%.1f,\"current\":%.2f,\"state\":\"%s\",\"ts_ms\":%lu}",
           vib, tmp, cur, STATE_NAME[s], (unsigned long)millis());
  mqtt.publish(MQTT_TOPIC, buf);
}

// ------------------------------------------------------------- setup
void setup() {
  Serial.begin(115200);
  pinMode(PIN_VIBRATION, INPUT);
  for (uint8_t p : {PIN_LED_RED, PIN_LED_GREEN, PIN_LED_YELLOW, PIN_BUZZER}) pinMode(p, OUTPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_TEMP, ADC_11db);
  analogSetPinAttenuation(PIN_CURRENT, ADC_11db);

  lcd.init(); lcd.backlight();
  lcd.setCursor(0, 0); lcd.print("Calibrating...");
  calibrateCurrentOffset();

  attachInterrupt(digitalPinToInterrupt(PIN_VIBRATION), onVibration, RISING);

  // TLS on the wire but no certificate check: a deliberate PROTOTYPE shortcut.
  // For production, replace with net.setCACert(<HiveMQ root CA>).
  net.setInsecure();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastSample = millis();
}

void loop() {
  maintainConnectivity();
  if (mqtt.connected()) mqtt.loop();

  if (millis() - lastSample < SAMPLE_MS) return;
  lastSample += SAMPLE_MS;

  noInterrupts(); uint16_t vib = vibPulses; vibPulses = 0; interrupts();
  float tmp = readTemperatureC();
  float cur = readCurrentA();
  State s = classify(vib, tmp, cur);

  driveOutputs(s);
  showLcd(tmp, cur, vib, s);
  publishReading(vib, tmp, cur, s);
  Serial.printf("vib=%u temp=%.1f cur=%.2f state=%s wifi=%d mqtt=%d\n",
                vib, tmp, cur, STATE_NAME[s], WiFi.status() == WL_CONNECTED, mqtt.connected());
}
