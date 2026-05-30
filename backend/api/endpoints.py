from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.system.schemas import AgentOrderRequest, RunSimulationRequest, SpeedRequest, StepRequest
from backend.system.simulation import Simulation

router = APIRouter()

simulation = Simulation()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "running": simulation.is_running(),
        "rabbitmq": simulation.rabbitmq.status,
        "rabbitmqExchange": simulation.rabbitmq.exchange,
    }


@router.get("/grid")
def get_grid():
    return simulation.snapshot()


@router.get("/snapshot")
def snapshot():
    return {"status": "ok", "snapshot": simulation.snapshot()}


@router.get("/messages")
def messages(limit: int = 100):
    return {"status": "ok", "messages": simulation.get_messages(limit=limit)}


@router.get("/config")
def config():
    return {"status": "ok", "config": simulation.get_config()}


@router.post("/run_simulation")
def run_simulation(payload: RunSimulationRequest | None = None):
    if simulation.is_running():
        raise HTTPException(status_code=400, detail="Simulation already running")

    config = payload.model_dump(exclude_none=True) if payload else {}
    simulation.start(config)
    return {
        "status": "ok",
        "message": "Simulation started",
        "simulationSessionId": simulation.simulation_session_id,
    }


@router.post("/stop_simulation")
def stop_simulation():
    was_running = simulation.is_running()
    simulation.stop()
    return {
        "status": "ok",
        "message": "Simulation stopped" if was_running else "Simulation was already stopped",
    }


@router.post("/step")
def step(payload: StepRequest | None = None):
    ticks = payload.ticks if payload else 1
    result = simulation.manual_step(ticks)
    stats = result.get("stats") or {}
    return {
        "status": "ok",
        "ticks": ticks,
        "sectors_on_fire": stats.get("fire_count", 0),
        "sensor_messages_count": 0,
        "snapshot": result,
    }


@router.post("/set_speed")
def set_speed(payload: SpeedRequest):
    try:
        simulation.set_tick_interval(payload.tickInterval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "tickInterval": simulation.tick_interval}


@router.post("/orderFireBrigade")
def order_fire_brigade(payload: AgentOrderRequest):
    if not simulation.is_running():
        raise HTTPException(status_code=400, detail="Simulation not running")

    try:
        simulation.order_agent(payload.model_dump(exclude_none=True), "fire_brigade")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "message": "Order received"}


@router.post("/orderForestPatrol")
def order_forest_patrol(payload: AgentOrderRequest):
    if not simulation.is_running():
        raise HTTPException(status_code=400, detail="Simulation not running")

    try:
        simulation.order_agent(payload.model_dump(exclude_none=True), "forester")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "message": "Order received"}
