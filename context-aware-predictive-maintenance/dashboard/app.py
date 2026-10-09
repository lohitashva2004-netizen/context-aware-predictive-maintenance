"""Plotly Dash operator dashboard.

Run locally without any hardware or broker:
    PDM_DEMO=1 python dashboard/app.py
Run against a live broker:
    export MQTT_HOST=... MQTT_USER=... MQTT_PASSWORD=...  &&  python dashboard/app.py
"""

from __future__ import annotations

import os
import threading
import time

import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from pdm.config import FEATURES, THRESHOLDS
from pdm.forecast import project_reading
from pdm.model import fault_probability, load_or_train, predict_label, predict_proba
from pdm.rules import channel_alerts
from pdm.simulate import run_scenario
from pdm.trend import classify_trend

from mqtt_client import start_subscriber
from state import TelemetryBuffer

COLORS = {"Normal": "#22c55e", "Warning": "#eab308", "Critical": "#ef4444", "Waiting": "#64748b"}
BG, CARD, TXT, MUTED = "#0b1220", "#111a2e", "#e2e8f0", "#94a3b8"
CHANNELS = [("temperature", "Temperature", "°C", 100), ("current", "Current", "A", 7), ("vibration", "Vibration", "pulses", 12)]

model = load_or_train()
buffer = TelemetryBuffer()


def _demo_feeder() -> None:
    """Replay the 100-second bench scenario in a loop (PDM_DEMO=1)."""
    while True:
        for _, reading in run_scenario():
            from pdm.rules import classify_reading
            buffer.add({**reading, "state": classify_reading(**reading)})
            time.sleep(2)


if os.environ.get("PDM_DEMO") == "1":
    threading.Thread(target=_demo_feeder, daemon=True).start()
else:
    start_subscriber(buffer)

app = Dash(__name__, title="Predictive Maintenance Dashboard")
server = app.server   # exposed for gunicorn: `gunicorn dashboard.app:server`


def card(*children, **style):
    return html.Div(children, style={"background": CARD, "borderRadius": "10px", "padding": "14px 18px", **style})


def label(text):
    return html.Div(text, style={"color": MUTED, "fontSize": "11px", "letterSpacing": "1.5px", "textTransform": "uppercase"})


def gauge(key, title, unit, vmax, value):
    lim = THRESHOLDS[key]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, number={"suffix": f" {unit}", "font": {"color": TXT, "size": 26}},
        title={"text": title, "font": {"color": MUTED, "size": 13}},
        gauge={"axis": {"range": [0, vmax], "tickcolor": MUTED}, "bar": {"color": TXT, "thickness": 0.2},
               "steps": [{"range": [0, lim["warning"]], "color": "#14532d"},
                         {"range": [lim["warning"], lim["critical"]], "color": "#713f12"},
                         {"range": [lim["critical"], vmax], "color": "#7f1d1d"}]}))
    fig.update_layout(height=190, margin=dict(l=20, r=20, t=40, b=5), paper_bgcolor=CARD, font={"color": TXT})
    return fig


def trend_fig(key, title, unit, times, values):
    lim = THRESHOLDS[key]
    fig = go.Figure(go.Scatter(x=times, y=values, mode="lines", line={"color": "#38bdf8", "width": 2}))
    fig.add_hline(y=lim["warning"], line={"color": COLORS["Warning"], "dash": "dot", "width": 1})
    fig.add_hline(y=lim["critical"], line={"color": COLORS["Critical"], "dash": "dot", "width": 1})
    fig.update_layout(title={"text": f"{title} ({unit})", "font": {"size": 13, "color": MUTED}}, height=210,
                      margin=dict(l=40, r=10, t=35, b=30), paper_bgcolor=CARD, plot_bgcolor=CARD,
                      font={"color": TXT}, xaxis={"showgrid": False, "nticks": 4}, yaxis={"gridcolor": "#1e293b"})
    return fig


def prob_bar(name, p):
    return html.Div([
        html.Div([html.Span(name), html.Span(f"{p * 100:.1f}%")], style={"display": "flex", "justifyContent": "space-between", "fontSize": "13px"}),
        html.Div(html.Div(style={"width": f"{p * 100:.1f}%", "height": "100%", "background": COLORS[name], "borderRadius": "4px", "transition": "width .6s"}),
                 style={"height": "8px", "background": "#1e293b", "borderRadius": "4px", "margin": "4px 0 10px"}),
    ])


def stat(title, value, sub="", color=TXT):
    return card(label(title), html.Div(value, style={"fontSize": "26px", "fontWeight": 700, "color": color, "margin": "6px 0 2px"}),
                html.Div(sub, style={"color": MUTED, "fontSize": "12px"}), flex="1", minWidth="170px")


app.layout = html.Div(style={"background": BG, "minHeight": "100vh", "color": TXT, "fontFamily": "Inter, Segoe UI, sans-serif", "padding": "20px"}, children=[
    html.Div([html.H2("Predictive Maintenance System", style={"margin": 0, "fontSize": "20px"}),
              html.Div(id="link", style={"color": MUTED, "fontSize": "13px"})],
             style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"}),
    html.Div(id="body"),
    dcc.Interval(id="tick", interval=2000, n_intervals=0),
])


@app.callback(Output("body", "children"), Output("link", "children"), Input("tick", "n_intervals"))
def refresh(_):
    snap = buffer.snapshot()
    if not snap["temperature"]:
        return card(html.Div("Waiting for the first reading from the edge node…", style={"color": MUTED})), "● no data yet"

    reading = {f: snap[f][-1] for f in FEATURES}
    probs = predict_proba(model, reading)
    state = predict_label(model, reading)
    projected = project_reading(snap)
    future_state = predict_label(model, projected) if projected else "Waiting"
    trend = classify_trend(snap)
    age = time.time() - snap["last_update"]
    alerts = channel_alerts(reading)
    if projected and future_state != "Normal" and state == "Normal":
        alerts.append({"channel": "Forecast", "level": "Warning", "value": 0, "unit": ""})

    def alert_row(a):
        text = (f"Projected {future_state} in ~20 s - act early" if a["channel"] == "Forecast"
                else f"{a['channel']} {a['level']}: {a['value']:g} {a['unit']}")
        return html.Div("■ " + text, style={"color": COLORS[a["level"]], "fontSize": "14px", "padding": "2px 0"})

    return html.Div([
        html.Div([
            card(label("Machine status"), html.Div(state.upper(), style={"fontSize": "40px", "fontWeight": 800, "color": COLORS[state]}),
                 html.Div(f"Firmware state: {snap['state'][-1]}", style={"color": MUTED, "fontSize": "12px"}), flex="1", minWidth="260px"),
            card(label("Active alerts"), *(([alert_row(a) for a in alerts]) or [html.Div("No active alerts - operating normally", style={"color": COLORS['Normal'], "marginTop": "8px"})]),
                 flex="2", minWidth="300px"),
        ], style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"}),
        html.Div([dcc.Graph(figure=gauge(k, t, u, m, reading[k]), config={"displayModeBar": False}, style={"flex": "1", "minWidth": "240px"})
                  for k, t, u, m in CHANNELS], style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"}),
        html.Div([stat("Random Forest state", state, f"P(fault) {fault_probability(probs) * 100:.1f}%", COLORS[state]),
                  stat("Forecast (~20 s)", future_state, "needs 3+ readings" if not projected else
                       f"{projected['temperature']:.1f} °C · {projected['current']:.2f} A · {projected['vibration']:.1f} pls", COLORS[future_state]),
                  stat("Sensor trend", {"Rising": "Rising ↑", "Falling": "Falling ↓", "Stable": "Stable →"}[trend],
                       "last 5 vs previous 5 readings", COLORS["Warning"] if trend == "Rising" else TXT),
                  card(label("Class probabilities"), html.Div([prob_bar(c, probs[c]) for c in ("Normal", "Warning", "Critical")], style={"marginTop": "8px"}), flex="2", minWidth="260px")],
                 style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"}),
        html.Div([dcc.Graph(figure=trend_fig(k, t, u, snap["time"], snap[k]), config={"displayModeBar": False}, style={"flex": "1", "minWidth": "260px"})
                  for k, t, u, _ in CHANNELS], style={"display": "flex", "gap": "14px", "flexWrap": "wrap"}),
    ]), f"● live · last reading {age:.0f}s ago"


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
