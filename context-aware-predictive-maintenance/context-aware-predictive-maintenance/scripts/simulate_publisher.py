"""Publish the 100-second bench scenario to the MQTT broker, standing in for the
ESP32. Lets you exercise the full cloud pipeline with no hardware attached.

    export MQTT_HOST=... MQTT_USER=... MQTT_PASSWORD=...
    python scripts/simulate_publisher.py            # loops forever, 2 s cadence
"""

import json
import os
import time

import paho.mqtt.client as mqtt

from pdm.rules import classify_reading
from pdm.simulate import run_scenario


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pdm-simulator")
    client.username_pw_set(os.environ["MQTT_USER"], os.environ["MQTT_PASSWORD"])
    client.tls_set()
    client.connect(os.environ["MQTT_HOST"], int(os.environ.get("MQTT_PORT", "8883")))
    client.loop_start()
    topic = os.environ.get("MQTT_TOPIC", "motor/all")
    while True:
        for t, reading in run_scenario():
            payload = {**reading, "state": classify_reading(**reading)}
            client.publish(topic, json.dumps(payload))
            print(f"t={t:3d}s  {payload}")
            time.sleep(2)


if __name__ == "__main__":
    main()
