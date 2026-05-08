from pydantic import BaseModel


class CellResponse(BaseModel):
    row: int
    col: int
    symbol_type: str


class GridResponse(BaseModel):
    cells: list[CellResponse]