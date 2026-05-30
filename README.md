# Wildfire Detection System

FastAPI + React wildfire simulation dashboard.

The project simulates fire spread on a grid, fire brigade and forest patrol movement, sensor telemetry, dispatch messages for emergency services, and optional RabbitMQ publishing.

## What It Does

- Runs a wildfire simulation on a configurable map.
- Uses a local rewriting-rule system inspired by formal production systems such as L-systems.
- Shows a live operational map in React.
- Supports fire brigade and forest patrol agents.
- Lets you load/edit simulation config as JSON.
- Emits messages for:
  - lifecycle events,
  - fire brigade orders,
  - forest patrol orders,
  - sensor telemetry,
  - agent telemetry,
  - fire service dispatch.
- Shows messages in the UI with pretty and raw JSON views.
- Optionally publishes all messages to RabbitMQ.

## Rewriting System Model

The fire simulation uses a local state rewriting system.

It is inspired by formal rewriting systems such as Lindenmayer systems (L-systems), but it does not rewrite a global string. Instead, it rewrites the state of map cells using local production rules and neighborhood/environment context.

Classical L-system example:

```text
Axiom: F
Production: F -> F[+F]F[-F]F
```

This project:

```text
Axiom / initial state: configured grid
Alphabet / states: TREE, FIRE, BURNED, WATER
Context: neighboring cells, wind, humidity, terrain type, patrol status
Productions:
  FIRE(level,burn) -> FIRE(level+growth,burn+damage)
  FIRE(burn>=100) -> BURNED
  TREE + adjacent FIRE + environment -> FIRE
```

The implementation lives in:

```text
backend/system/rules.py
```

The grid delegates fire evolution to `FirePropagationRules`, which applies production rules every simulation tick. This keeps the simulation rule-based and easier to explain than hard-coded fire logic embedded directly in the grid.

This is best described as:

```text
local grid rewriting system inspired by L-systems / production systems
```

not as a pure classical Lindenmayer string-rewriting system.

The UI also has a **Rules** tab. It shows the current rewriting model, configured production rules, and the rules that were applied in the latest simulation summary message. This is useful during demos because it makes the formal model visible without opening the backend code.

## Requirements

- Python virtualenv in `backend/venv`
- Node.js / npm
- Docker Desktop, only if you want RabbitMQ auto-start

## Quick Start

From the project root:

```bash
cd /Wildfire_detection_system
./scripts/dev.sh
```

This starts:

- RabbitMQ via Docker Compose
- FastAPI backend on `http://127.0.0.1:8000`
- Vite frontend on `http://127.0.0.1:5173`

Open:

```text
http://127.0.0.1:5173
```

Press Enter or click **Open Operations Console**.

## Manual Start

### 1. RabbitMQ

RabbitMQ is optional for UI testing, but useful if you want real message broker publishing.

```bash
docker compose up -d rabbitmq
```

Management UI:

```text
http://localhost:15672
```

Login:

```text
guest / guest
```

### 2. Backend

```bash
backend/venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

If RabbitMQ is running, `rabbitmq` should become `connected`.

### 3. Frontend

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

## RabbitMQ

The backend publishes messages to the topic exchange:

```text
wildfire.simulation
```

Examples of routing keys:

```text
simulation.control.lifecycle
simulation.control.fire_brigade_actions
simulation.control.forester_actions
simulation.dispatch.fire_services
simulation.telemetry.summary
simulation.telemetry.agents.batch
simulation.telemetry.sensors.temp_humidity
simulation.telemetry.sensors.wind_speed
simulation.telemetry.sensors.wind_direction
simulation.telemetry.sensors.litter_moisture
simulation.telemetry.sensors.co2
simulation.telemetry.sensors.pm2_5
simulation.telemetry.sensors.camera
simulation.events
```

The UI still works without RabbitMQ because it reads from the backend's in-memory message log. RabbitMQ is for integration with other services.

### Why RabbitMQ Exists Here

RabbitMQ works like a broker/socket hub between this simulation and other systems.

Instead of making every external service call the simulation directly, the simulation publishes messages to RabbitMQ. Other services can subscribe to the messages they care about.

Conceptually:

```text
Simulation Backend -> RabbitMQ -> Fire Service System
Simulation Backend -> RabbitMQ -> Sensor Analytics
Simulation Backend -> RabbitMQ -> Decision Support
Simulation Backend -> RabbitMQ -> Logging / Monitoring
```

This means:

- the simulation does not need to know who consumes its data,
- many consumers can receive the same event,
- consumers can be added later without changing simulation logic,
- services are more loosely coupled,
- the UI can still work even if RabbitMQ is offline.

RabbitMQ is therefore an integration layer. The in-memory UI message log is for easy local visualization; RabbitMQ is for external systems.

## Message Structure

Every message created by the simulation has the same outer envelope:

```json
{
  "id": 31,
  "tick": 25,
  "topic": "simulation.dispatch.fire_services",
  "direction": "out",
  "payload": {},
  "timestamp": 1779999999.123
}
```

Fields:

- `id` - global message id inside the backend message bus. This counts every message, not just messages visible in one UI tab.
- `tick` - simulation tick when the message was created.
- `topic` - routing key / message category.
- `direction` - currently mostly `out`, meaning emitted by the simulation.
- `payload` - actual message data.
- `timestamp` - Unix timestamp when the backend created the message.

Because `id` is global, numbers can skip inside filtered UI tabs. For example, the **Dispatch** tab may show `bus id #31` and then `bus id #40` because sensor messages, telemetry, or events were created between them.

### Dispatch Message

Topic:

```text
simulation.dispatch.fire_services
```

Purpose:

This message is intended for emergency/fire services. It says where the fire is, how severe it is, what the environment looks like, and what the system recommends.

Example:

```json
{
  "title": "FIRE EXPANSION ALERT",
  "event": "fire_detected",
  "recipient": "fire_services",
  "priority": "high",
  "fire": {
    "row": 10,
    "col": 10,
    "sectorId": 211,
    "sectorType": "TREE",
    "location": {
      "latitude": 52.271805,
      "longitude": 21.054305
    },
    "fireLevel": 42.5,
    "burnLevel": 10.2
  },
  "environment": {
    "windSpeed": 3.4,
    "windSpeedUnit": "m/s",
    "windDirection": "W",
    "windDirectionUnit": "cardinal",
    "humidity": 41.2,
    "humidityUnit": "%"
  },
  "recommendation": "Dispatch nearest available brigade and keep patrols ahead of wind direction."
}
```

Priority values:

```text
watch
high
critical
```

### Sensor Messages

Sensor messages are emitted under:

```text
simulation.telemetry.sensors.*
```

They represent what a real sensor network might send.

Temperature and humidity:

```text
simulation.telemetry.sensors.temp_humidity
```

```json
{
  "sensorId": "S-211-TH",
  "sectorId": 211,
  "sectorType": "TREE",
  "location": {
    "latitude": 52.271805,
    "longitude": 21.054305
  },
  "temperature": 38.2,
  "temperatureUnit": "C",
  "humidity": 37.5,
  "humidityUnit": "%"
}
```

Wind speed:

```text
simulation.telemetry.sensors.wind_speed
```

```json
{
  "sensorId": "S-211-WS",
  "sectorId": 211,
  "windSpeed": 3.4,
  "windSpeedUnit": "m/s"
}
```

Wind direction:

```text
simulation.telemetry.sensors.wind_direction
```

```json
{
  "sensorId": "S-211-WD",
  "sectorId": 211,
  "windDirection": "W",
  "windDirectionUnit": "cardinal"
}
```

Litter moisture:

```text
simulation.telemetry.sensors.litter_moisture
```

```json
{
  "sensorId": "S-211-LM",
  "sectorId": 211,
  "litterMoisture": 24.8,
  "litterMoistureUnit": "%"
}
```

CO2:

```text
simulation.telemetry.sensors.co2
```

```json
{
  "sensorId": "S-211-CO2",
  "sectorId": 211,
  "co2": 760.2,
  "co2Unit": "ppm"
}
```

PM2.5:

```text
simulation.telemetry.sensors.pm2_5
```

```json
{
  "sensorId": "S-211-PM25",
  "sectorId": 211,
  "pm2_5": 85.3,
  "pm2_5Unit": "ug/m3"
}
```

Camera / smoke detection:

```text
simulation.telemetry.sensors.camera
```

```json
{
  "sensorId": "S-211-CAM",
  "sectorId": 211,
  "smokeDetected": true,
  "smokeLevel": 72.4,
  "smokeLevelUnit": "index",
  "fireVisible": true
}
```

### Agent Command Messages

Fire brigade command:

```text
simulation.control.fire_brigade_actions
```

```json
{
  "event": "agent_order",
  "agentId": "FB-1",
  "task": "extinguish",
  "sectorId": null,
  "target": {
    "row": 10,
    "col": 10
  }
}
```

Forest patrol command:

```text
simulation.control.forester_actions
```

```json
{
  "event": "agent_order",
  "agentId": "FP-1",
  "task": "patrol",
  "sectorId": null,
  "target": {
    "row": 5,
    "col": 5
  }
}
```

### Agent Telemetry Batch

Topic:

```text
simulation.telemetry.agents.batch
```

Purpose:

Sends current positions and states of all agents.

```json
{
  "batch": [
    {
      "agent_id": "FB-1",
      "type": "fire_brigade",
      "row": 4.2,
      "col": 3.8,
      "state": "TRAVELLING",
      "target_row": 10,
      "target_col": 10
    }
  ]
}
```

### Simulation Summary

Topic:

```text
simulation.telemetry.summary
```

Purpose:

Compact state of the simulation.

```json
{
  "tick": 25,
  "running": true,
  "fire_count": 4,
  "burned_count": 2,
  "tree_count": 394,
  "agent_count": 3,
  "simulation_session_id": "sim_1779999999",
  "rewritingSystem": "local-grid-production-system",
  "productions": [
    "fire-growth: FIRE(level,burn) -> FIRE(level+growth,burn+damage)",
    "burnout: FIRE(burn>=100) -> BURNED",
    "fire-spread: TREE + adjacent FIRE + environment -> FIRE"
  ],
  "lastAppliedRules": [
    "fire-growth",
    "fire-spread"
  ]
}
```

Rewriting fields:

- `rewritingSystem` - name of the formal rewriting model used by the simulation.
- `productions` - readable production rules available in the simulation.
- `lastAppliedRules` - rules that actually fired during the latest tick/generation.

### Lifecycle Messages

Topic:

```text
simulation.control.lifecycle
```

Start:

```json
{
  "event": "simulation_started",
  "simulationSessionId": "sim_1779999999",
  "rows": 20,
  "columns": 20,
  "agents": ["FB-1", "FB-2", "FP-1"]
}
```

Stop:

```json
{
  "event": "simulation_stopped",
  "simulationSessionId": "sim_1779999999"
}
```

### Runtime Events

Topic:

```text
simulation.events
```

Purpose:

Agent and simulation runtime events.

Examples:

```json
{
  "tick": 31,
  "agentId": "FB-1",
  "event": "reached_fire"
}
```

```json
{
  "tick": 44,
  "agentId": "FB-1",
  "event": "fire_extinguished"
}
```

## UI Overview

The operations console has:

- **Operational Map** - live grid with fire, burned cells, agents, and sectors.
- **Dispatch tab** - messages intended for fire services, including fire location, lat/lon, wind, humidity, severity, and recommendation.
- **Messages tab** - general message bus view.
- **Sensors tab** - sensor telemetry messages.
- **Rules tab** - current rewriting model, production rules, and last applied rules.
- **Config tab** - loaded configuration summary and raw JSON editor.

Agent colors:

- Blue circle: fire brigade
- Yellow circle: forest patrol
- Red cell: fire
- Green cell: forest/tree
- Gray cell: burned
- Blue cell: water

## Basic Test Flow

1. Start the app.
2. Open the operations console.
3. Click **Start** or go to **Config** and click **Apply**.
4. Watch `Tick`, `Fires`, and `RabbitMQ` status.
5. Open **Dispatch** to see fire service messages.
6. Open **Sensors** to see sensor telemetry.
7. Select `FB-1` and click a fire cell to send a brigade.
8. Select `FP-1` and click a cell to send a patrol.
9. Use **Raw JSON** buttons to inspect exact message/config payloads.

## API Endpoints

```text
GET  /health
GET  /grid
GET  /snapshot
GET  /messages?limit=100
GET  /config
POST /run_simulation
POST /stop_simulation
POST /step
POST /set_speed
POST /orderFireBrigade
POST /orderForestPatrol
```

Example start:

```bash
curl -X POST http://127.0.0.1:8000/run_simulation \
  -H "Content-Type: application/json" \
  -d '{}'
```

Example brigade order:

```bash
curl -X POST http://127.0.0.1:8000/orderFireBrigade \
  -H "Content-Type: application/json" \
  -d '{"fireBrigadeId":1,"row":10,"col":10,"action":"EXTINGUISH"}'
```

Example patrol order:

```bash
curl -X POST http://127.0.0.1:8000/orderForestPatrol \
  -H "Content-Type: application/json" \
  -d '{"foresterPatrolId":1,"row":5,"col":5,"action":"PATROL"}'
```

## Config Format

You can edit this in the UI under **Config -> Raw JSON**.

```json
{
  "rows": 20,
  "columns": 20,
  "sectors": [
    {
      "row": 10,
      "column": 10,
      "sectorType": "TREE",
      "initialState": {
        "fireLevel": 35
      }
    }
  ],
  "fireBrigades": [
    { "fireBrigadeId": 1, "row": 0, "col": 0 }
  ],
  "foresterPatrols": [
    { "foresterPatrolId": 1, "row": 19, "col": 0 }
  ]
}
```

Supported sector type examples:

```text
TREE
FOREST
CONIFEROUS
GRASS
MEADOW
WATER
```

Sector type affects fire spread probability.

## Verification

Backend syntax check:

```bash
backend/venv/bin/python -m compileall backend/api backend/system backend/core
```

Frontend build:

```bash
cd frontend
npm run build
```

## Notes

- RabbitMQ is optional for local UI demos.
- If `/health` shows `rabbitmq: disconnected`, start RabbitMQ with `docker compose up -d rabbitmq` and restart the backend.
- The message ID shown in the UI is global for the whole in-memory message bus, so IDs can skip inside filtered tabs.
