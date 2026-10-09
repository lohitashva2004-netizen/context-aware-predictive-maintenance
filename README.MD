Context-Aware Predictive Maintenance of Industrial Drive Motors
A sub-₹1,000 edge-to-cloud monitoring system that watches vibration, temperature and current together, classifies motor health with a Random Forest, and warns ~20 seconds before a fault threshold is crossed.
![CI](https://github.com/<your-username>/context-aware-predictive-maintenance/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![ESP32](https://img.shields.io/badge/hardware-ESP32--WROOM--32-red)
![License](https://img.shields.io/badge/license-MIT-green)
B.Tech final-year project, Dept. of Electronics and Communication Engineering, SRM Institute of Science and Technology (Vadapalani), supervised by Dr. R. Sathiya. The work was accepted and presented at the 17th International Conference on Science & Innovative Engineering (ICSIE 2026), Chennai.
<p align="center">
  <img src="docs/images/fig03_breadboard_prototype.jpg" width="48%" alt="Breadboard prototype showing T:35.0C I:0.0A Vib:0 Normal on the LCD">
  <img src="docs/images/fig05_dashboard_normal.jpg" width="48%" alt="Python Dash dashboard during normal operation">
</p>
---
Why this exists
A printing press in Chennai lost its cylinder drive mid-run twice in six months. Each time the paper web tore and the crew spent hours rethreading. The only monitoring on the floor was a handheld vibration meter, pointed at the motor once a fortnight. Commercial predictive-maintenance systems would have caught it, but they are priced for large process plants.
Published condition-monitoring work tends to leave three gaps for a small or medium enterprise:
Cost. Dedicated edge hardware and multi-sensor arrays are out of budget.
Connectivity. Many designs assume a stable cloud link, which is not realistic next to welding sets, three-phase motors and a crowded 2.4 GHz band.
Explainability. A bare probability score doesn't tell an operator which sensor tripped, and they may have ten seconds to decide whether to stop the press.
This project tries to close all three with one hardware stack that costs under ₹1,000.
What it does
Samples vibration, motor-casing temperature and motor current every 2 s on an ESP32.
Runs a deterministic Normal / Warning / Critical check on the device, so the LCD, LEDs and buzzer keep working with no Wi-Fi or cloud.
Publishes each reading over TLS-secured MQTT to HiveMQ Cloud.
A Python Dash dashboard classifies every reading with a 100-tree Random Forest and shows per-class probabilities.
Fits a least-squares line to the last 10 readings per channel, projects 10 steps (~20 s) ahead, and passes the projection through the same forest, so the forecast and the live view share one model.
Names the offending channel in the alerts list and shows a simple Rising / Falling / Stable trend indicator for operators who don't have time to read probability bars.
Architecture
![Three-layer architecture](docs/images/fig01_system_architecture.jpg)
```
 SW420 ─┐                                                    ┌─ Gauges, trends, alerts
 LM35  ─┼─▶ ESP32 ──TLS MQTT (8883)──▶ HiveMQ ──WSS (8884)──▶ Dash app on Render
 ACS712─┘     │  local thresholds                            │  Random Forest + forecast
              └─▶ LCD · LED · buzzer (works offline)         └─ trend indicator
```
The design is a hybrid: hard safety logic stays on the edge node, probabilistic intelligence lives on the dashboard. The layers are deliberately loosely coupled. The ESP32 keeps alarming if the network drops, and the dashboard keeps producing output for roughly two minutes if the edge node disconnects, because it holds a 60-reading buffer per channel.
More detail: docs/architecture.md · docs/hardware.md
Hardware
Component	Role
ESP32-WROOM-32	Acquisition, local classification, MQTT publication
SW420 vibration sensor	Vibration pulse count per 2 s window
LM35	Motor casing temperature (10 mV/°C)
ACS712 (5 A) + 10 kΩ/20 kΩ divider	Motor current, scaled from 5 V to the 3.3 V ADC range
16×2 I²C LCD, 3 LEDs, piezo buzzer	Local readout and alerts
Total bill of materials: under ₹1,000. Full pin map and schematic in docs/hardware.md.
<p align="center"><img src="docs/images/fig02_proteus_schematic.jpg" width="75%" alt="Proteus 9 schematic"></p>
Repository layout
```
├── firmware/esp32_edge_node/   Arduino sketch for the ESP32 (config.example.h for credentials)
├── src/pdm/                    Core analytics: thresholds, dataset, Random Forest, forecast, trend
├── dashboard/                  Plotly Dash app + MQTT-over-WebSocket subscriber
├── ml/train_model.py           Dataset generation and model training
├── models/                     Trained forest (rf_model.joblib) and training report
├── data/                       The synthetic training set (CSV)
├── scripts/                    Hardware-free MQTT publisher and scenario replay
├── tests/                      34 unit tests (thresholds, forecast, trend, model)
├── docs/                       Architecture, hardware, results, and report figures
└── render.yaml · Procfile      One-click deployment config for Render
```
Quick start
1. Try the dashboard with no hardware and no broker
```bash
git clone https://github.com/<your-username>/context-aware-predictive-maintenance.git
cd context-aware-predictive-maintenance
pip install -e ".[dashboard,dev]"
PDM_DEMO=1 python dashboard/app.py          # open http://localhost:8050
```
Demo mode replays a simulated 100-second scenario (idle → bearing disturbance → overload → thermal rise) in a loop.
2. Run the tests
```bash
pytest -q
```
3. Retrain the model
```bash
python ml/train_model.py                    # regenerates data/, models/
python scripts/replay_scenario.py           # regenerates docs/images/replay_summary.png
```
4. Run against a real broker
```bash
cp .env.example .env                        # fill in your HiveMQ Cloud credentials
export $(grep -v '^#' .env | xargs)
python dashboard/app.py                     # live dashboard
python scripts/simulate_publisher.py        # in another terminal: stand-in for the ESP32
```
5. Flash the ESP32
Install the Arduino-ESP32 core, then the `PubSubClient` and `LiquidCrystal_I2C` libraries.
Copy `firmware/esp32_edge_node/config.example.h` to `config.h` and fill in Wi-Fi and HiveMQ details.
Wire the board following docs/hardware.md, open `esp32_edge_node.ino`, and upload.
With the motor off, power up once so the ACS712 zero-current offset is calibrated.
6. Deploy the dashboard to Render's free tier using `render.yaml`, and set `MQTT_HOST`, `MQTT_USER` and `MQTT_PASSWORD` as environment variables. A deployed instance from the original project: https://esp32-machine-dashboard-5.onrender.com/ (free-tier services sleep when idle, so the first load can take a minute).
Fault thresholds
Calibrated for the small single-phase laboratory motor. Any production drive needs recalibration against its nameplate.
Parameter	Warning (above)	Critical (above)
Temperature	55 °C	70 °C
Current	3.0 A	4.5 A
Vibration	3 pulses / 2 s	7 pulses / 2 s
Results (bench tests on a single-phase induction motor)
Faults were simulated: bearing impulses by perturbing the SW420, thermal faults by partly blocking the ventilation slots, and overload with a belt-driven load.
Indicator	Measured
Fault state transitions	Classified correctly across all test cases
End-to-end latency, sensor → dashboard	2 to 4 s
MQTT connection after Wi-Fi association	within 3 s
Forecast lead time before the thermal threshold	4 to 6 readings (8 to 12 s)
False positives during normal operation	None observed
Local LED / buzzer response on Critical	within one acquisition cycle
Bill of materials	under ₹1,000
<p align="center">
  <img src="docs/images/fig06_sensor_signals.jpg" width="48%" alt="Three sensor channels over a 100 second run">
  <img src="docs/images/fig07_severity_classification.jpg" width="48%" alt="Severity classification over the same run">
</p>
The three channels light up at different moments (vibration at 30 s, current around 55 s, temperature drifting across both), so a single-channel monitor would have seen only part of the story. Full write-up in docs/results.md.
The figure below is a software replay produced by this repository (`scripts/replay_scenario.py`), which pushes a simulated version of that scenario through the trained forest. It is not recorded sensor data. Note how the forecast reacts early, but also briefly flickers to Warning on idle noise near 10 s, a real weakness of straight-line extrapolation.
<p align="center"><img src="docs/images/replay_summary.png" width="70%" alt="Software replay of the simulated scenario"></p>
Limitations
These are listed up front on purpose. Knowing what a prototype does not show matters as much as what it does.
Synthetic training data. No labelled real-fault recordings were available, so the forest was trained on ~1,000 samples generated from the threshold-defined regions of the feature space. It learns the threshold geometry, not real degradation patterns. The ~99.6% hold-out score printed by `ml/train_model.py` is therefore a sanity check, not evidence of real-world accuracy, because the labels come from the same rules.
Coarse vibration sensing. The SW420 counts contact closures. It can't resolve frequency-domain bearing signatures; a MEMS accelerometer with FFT analysis is the obvious upgrade.
Casing, not winding, temperature. The LM35 sits on the motor body and lags the winding temperature.
Small motors only. The 5 A ACS712 limits the prototype to small single-phase machines.
Linear forecast. Real fault progressions are rarely monotone. Within a ~20 s horizon it is adequate for early warning, but it is noise-sensitive and over-reacts to step changes.
Prototype security shortcut. The ESP32 uses TLS without certificate verification (`setInsecure()`); production should pin the broker's CA certificate.
Breadboard build. Fine for bench validation, not for shop-floor use.
Roadmap
[ ] MEMS accelerometer + FFT-based bearing defect frequency analysis on the edge
[ ] DS18B20 digital temperature sensor (removes the analog clamp logic)
[ ] Clamp-type CT for three-phase, higher-current drives
[ ] Train on real motor-fault recordings from a partner facility
[ ] TinyML quantisation so inference runs fully on the ESP32
[ ] Custom PCB with 3.3 V LDO, screw terminals and an industrial enclosure
[ ] Field validation on a working web offset press and an air compressor
Team
Lohitashva V S
Prabhanjan G H
Jayaprakash L
Supervisor: Dr. R. Sathiya, Assistant Professor, Dept. of ECE, SRM IST Vadapalani
Citation
If this is useful to you, see `CITATION.cff`. Selected references: Breiman (2001) Random Forests; Yan & Ma (2020) on induction-motor fault diagnosis; Cummins et al. (2024) on explainable predictive maintenance; Ciobotaru et al. (2025) on air-compressor predictive maintenance. The full list is in the project report.
License
MIT, see LICENSE.
