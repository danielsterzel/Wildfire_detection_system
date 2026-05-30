from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any

from backend.system.agents import AgentTask
from backend.system.grid import Grid
from backend.system.rabbitmq_publisher import RabbitMQPublisher


class Simulation:
    def __init__(self, grid_arg: Grid | None = None):
        self.grid = grid_arg if grid_arg else Grid.from_config(None)
        self.tick_count = 0
        self.tick_interval = 0.75
        self.simulation_session_id: str | None = None
        self._running = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self.events: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []
        self._message_id = 0
        self.current_config: dict[str, Any] = self._default_config()
        self._last_dispatch_ts = 0.0
        self.rabbitmq = RabbitMQPublisher()

    def start(self, config: dict | None = None) -> None:
        with self._lock:
            if self._running:
                return
            self.grid = Grid.from_config(config)
            self.current_config = deepcopy(config) if config else self._default_config()
            self.tick_count = 0
            self.simulation_session_id = f"sim_{int(time.time())}"
            self.messages = []
            self.events = []
            self._message_id = 0
            self._last_dispatch_ts = 0.0
            self._publish(
                "simulation.control.lifecycle",
                {
                    "event": "simulation_started",
                    "simulationSessionId": self.simulation_session_id,
                    "rows": self.grid.rows,
                    "columns": self.grid.columns,
                    "agents": list(self.grid.agents.keys()),
                },
            )
            self._stop.clear()
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SimulationLoop")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._publish(
                "simulation.control.lifecycle",
                {
                    "event": "simulation_stopped",
                    "simulationSessionId": self.simulation_session_id,
                },
            )
            self._running = False
            self._thread = None

    def is_running(self) -> bool:
        return self._running

    def set_tick_interval(self, value: float) -> None:
        if value <= 0:
            raise ValueError("tickInterval must be > 0")
        self.tick_interval = float(value)
        self._publish("simulation.control.speed", {"tickInterval": self.tick_interval})

    def manual_step(self, ticks: int = 1) -> dict:
        ticks = max(1, int(ticks))
        with self._lock:
            for _ in range(ticks):
                self._tick_once()
            return self.snapshot()

    def snapshot(self) -> dict:
        response = self.grid.to_response(
            tick=self.tick_count,
            running=self._running,
            simulation_session_id=self.simulation_session_id,
            messages=self.get_messages(limit=20),
        )
        return response.model_dump()

    def get_messages(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        return self.messages[-limit:]

    def get_config(self) -> dict[str, Any]:
        return deepcopy(self.current_config)

    def order_agent(self, order: dict, agent_kind: str) -> None:
        agent_id = self._normalize_agent_id(order, agent_kind)
        with self._lock:
            agent = self.grid.agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent not found: {agent_id}")

            task = self._build_task(order, agent_kind)
            agent.assign(task)
            event = {
                "tick": self.tick_count,
                "type": "agent_order",
                "agentId": agent_id,
                "task": task.task_type,
                "sectorId": task.sector_id,
                "target": {"row": task.target_row, "col": task.target_col},
            }
            self.events.append(event)
            self._publish(
                "simulation.control.fire_brigade_actions" if agent_kind == "fire_brigade" else "simulation.control.forester_actions",
                {
                    "event": "agent_order",
                    "agentId": agent_id,
                    "task": task.task_type,
                    "sectorId": task.sector_id,
                    "target": {"row": task.target_row, "col": task.target_col},
                }
            )

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                self._tick_once()
            time.sleep(self.tick_interval)

    def _tick_once(self) -> None:
        self.tick_count += 1
        delta = max(self.tick_interval, 0.05)
        for agent in list(self.grid.agents.values()):
            event = agent.update(self.grid, delta)
            if event.get("event") not in {"idle", "moving"}:
                agent_event = {"tick": self.tick_count, "agentId": agent.agent_id, **event}
                self.events.append(agent_event)
                self._publish("simulation.events", agent_event)
        self.grid.step_fire()
        if self.tick_count % 5 == 0:
            snapshot = self.grid.to_response(
                tick=self.tick_count,
                running=self._running,
                simulation_session_id=self.simulation_session_id,
            )
            stats = snapshot.stats.model_dump() if snapshot.stats else {}
            stats["rewritingSystem"] = "local-grid-production-system"
            stats["productions"] = self.grid.rewrite_rules.productions
            stats["lastAppliedRules"] = sorted(set(self.grid.last_applied_rules))
            self._publish("simulation.telemetry.summary", stats)
            self._publish(
                "simulation.telemetry.agents.batch",
                {"batch": [agent.to_response() for agent in self.grid.agents.values()]},
            )
            for topic, payload in self.grid.sensor_messages():
                self._publish(topic, payload)
            self._publish_service_dispatches()

    def _normalize_agent_id(self, order: dict, agent_kind: str) -> str:
        if agent_kind == "fire_brigade":
            raw = order.get("fireBrigadeId") or order.get("agentId")
            if raw is None:
                raise ValueError("fireBrigadeId or agentId is required")
            raw = str(raw)
            return raw if raw.startswith("FB-") else f"FB-{raw}"

        raw = order.get("foresterPatrolId") or order.get("agentId")
        if raw is None:
            raise ValueError("foresterPatrolId or agentId is required")
        raw = str(raw)
        return raw if raw.startswith("FP-") else f"FP-{raw}"

    def _build_task(self, order: dict, agent_kind: str) -> AgentTask:
        if order.get("goingToBase") or order.get("action") == "GO_TO_BASE":
            return AgentTask(task_type="return_to_base", description=order.get("description") or "Return to base")

        sector_id = order.get("targetSectorId") or order.get("sectorId")
        target = self.grid.sector_id_to_cell(sector_id)

        if target is None and order.get("location"):
            target = tuple(int(round(value)) for value in self.grid.location_to_cell(order["location"]))

        if target is None and order.get("row") is not None and order.get("col") is not None:
            target = int(order["row"]), int(order["col"])

        if target is None:
            raise ValueError("Order requires sectorId, location, or row/col")

        row, col = target
        action = str(order.get("action") or "").upper()
        if agent_kind == "fire_brigade":
            task_type = "extinguish" if action in {"", "EXTINGUISH"} else "move_to"
        else:
            task_type = "patrol" if action in {"", "PATROL"} else "move_to"

        return AgentTask(
            task_type=task_type,
            target_row=row,
            target_col=col,
            sector_id=sector_id,
            description=order.get("description") or order.get("reason") or "",
            priority=int(order.get("priority") or 10),
        )

    def _publish(self, topic: str, payload: dict[str, Any], direction: str = "out") -> None:
        self._message_id += 1
        message = {
            "id": self._message_id,
            "tick": self.tick_count,
            "topic": topic,
            "direction": direction,
            "payload": payload,
            "timestamp": time.time(),
        }
        self.messages.append(message)
        self.rabbitmq.publish(topic, message)
        if len(self.messages) > 500:
            self.messages = self.messages[-500:]

    def _publish_service_dispatches(self) -> None:
        now = time.time()
        if now - self._last_dispatch_ts < 5.0:
            return
        self._last_dispatch_ts = now

        for fire in self.grid.active_fires()[:5]:
            severity = "critical" if fire["fireLevel"] >= 65 else "high" if fire["fireLevel"] >= 35 else "watch"
            self._publish(
                "simulation.dispatch.fire_services",
                {
                    "title": "FIRE EXPANSION ALERT",
                    "event": "fire_detected",
                    "recipient": "fire_services",
                    "priority": severity,
                    "fire": fire,
                    "environment": {
                        "windSpeed": self.grid.wind_speed,
                        "windSpeedUnit": "m/s",
                        "windDirection": self.grid.wind_direction,
                        "windDirectionUnit": "cardinal",
                        "humidity": self.grid.humidity,
                        "humidityUnit": "%",
                    },
                    "recommendation": "Dispatch nearest available brigade and keep patrols ahead of wind direction.",
                },
            )

    def _default_config(self) -> dict[str, Any]:
        return {
            "rows": 20,
            "columns": 20,
            "sectors": [
                {
                    "row": 10,
                    "column": 10,
                    "sectorType": "TREE",
                    "initialState": {"fireLevel": 35},
                },
                {
                    "row": 11,
                    "column": 10,
                    "sectorType": "TREE",
                    "initialState": {"fireLevel": 15},
                },
            ],
            "fireBrigades": [
                {"fireBrigadeId": 1, "row": 0, "col": 0},
                {"fireBrigadeId": 2, "row": 19, "col": 19},
            ],
            "foresterPatrols": [{"foresterPatrolId": 1, "row": 19, "col": 0}],
        }
