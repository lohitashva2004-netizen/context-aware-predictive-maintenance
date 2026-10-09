"""Background MQTT-over-WebSocket subscriber (HiveMQ Cloud, TLS, port 8884).

Render's free tier restricts raw TCP on non-standard ports, so the dashboard uses
the broker's WebSocket endpoint instead of the port 8883 path the ESP32 uses.
"""

from __future__ import annotations

import json
import logging
import os

import paho.mqtt.client as mqtt

from state import TelemetryBuffer

log = logging.getLogger("pdm.mqtt")


def start_subscriber(buffer: TelemetryBuffer) -> mqtt.Client | None:
    host = os.environ.get("MQTT_HOST")
    if not host:
        log.warning("MQTT_HOST not set - subscriber not started")
        return None
    topic = os.environ.get("MQTT_TOPIC", "motor/all")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    client.username_pw_set(os.environ.get("MQTT_USER", ""), os.environ.get("MQTT_PASSWORD", ""))
    client.tls_set()                       # verifies the broker certificate
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(c, userdata, flags, reason_code, properties):
        log.info("MQTT connected (%s) - subscribing to %s", reason_code, topic)
        c.subscribe(topic)                 # re-subscribe after every reconnect

    def on_message(c, userdata, msg):
        try:
            buffer.add(json.loads(msg.payload))
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("Dropped malformed payload %r: %s", msg.payload[:80], exc)

    client.on_connect, client.on_message = on_connect, on_message
    client.connect_async(host, int(os.environ.get("MQTT_WS_PORT", "8884")), keepalive=30)
    client.loop_start()                    # daemon network thread; never blocks HTTP
    return client
