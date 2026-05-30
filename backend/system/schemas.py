from typing import Any, Optional
from pydantic import BaseModel, Field


class CellResponse(BaseModel):
    row: int
    col: int
    symbol_type: str
    sector_id: int
    sector_type: str
    fire_level: float = 0.0
    burn_level: float = 0.0
    extinguish_level: float = 0.0


class AgentResponse(BaseModel):
    agent_id: str
    type: str
    row: float
    col: float
    state: str
    target_row: Optional[int] = None
    target_col: Optional[int] = None
    sector_id: Optional[int] = None


class SimulationStats(BaseModel):
    tick: int
    running: bool
    fire_count: int
    burned_count: int
    tree_count: int
    agent_count: int
    simulation_session_id: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    tick: int
    topic: str
    direction: str
    payload: dict[str, Any]
    timestamp: float


class GridResponse(BaseModel):
    cells: list[CellResponse]
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    humidity: Optional[float] = None
    sectors: Optional[list[dict]] = None
    agents: list[AgentResponse] = Field(default_factory=list)
    messages: list[MessageResponse] = Field(default_factory=list)
    stats: Optional[SimulationStats] = None


class RunSimulationRequest(BaseModel):
    rows: Optional[int] = None
    columns: Optional[int] = None
    size: Optional[int] = None
    forestId: Optional[str] = None
    forestName: Optional[str] = None
    sectors: Optional[list[dict[str, Any]]] = None
    fireBrigades: Optional[list[dict[str, Any]]] = None
    foresterPatrols: Optional[list[dict[str, Any]]] = None
    sensors: Optional[list[dict[str, Any]]] = None
    cameras: Optional[list[dict[str, Any]]] = None
    location: Optional[list[dict[str, Any]]] = None


class StepRequest(BaseModel):
    ticks: int = 1


class SpeedRequest(BaseModel):
    tickInterval: float


class AgentOrderRequest(BaseModel):
    agentId: Optional[str | int] = None
    fireBrigadeId: Optional[str | int] = None
    foresterPatrolId: Optional[str | int] = None
    action: Optional[str] = None
    sectorId: Optional[int] = None
    targetSectorId: Optional[int] = None
    location: Optional[dict[str, float]] = None
    row: Optional[int] = None
    col: Optional[int] = None
    goingToBase: bool = False
    description: Optional[str] = None
    reason: Optional[str] = None
    priority: int = 10
