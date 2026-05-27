from typing import Optional
from pydantic import BaseModel


class CellResponse(BaseModel):
    row: int
    col: int
    symbol_type: str


class GridResponse(BaseModel):
    cells: list[CellResponse]
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    humidity: Optional[float] = None
    sectors: Optional[list[dict]] = None