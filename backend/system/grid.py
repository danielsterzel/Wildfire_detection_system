from __future__ import annotations

from dataclasses import dataclass
import random
from threading import RLock

from backend.system.agents import Agent, FireBrigade, ForesterPatrol
from backend.system.rules import FirePropagationRules
from backend.system.schemas import AgentResponse, CellResponse, GridResponse, MessageResponse, SimulationStats
from backend.system.symbols import Burned, Fire, Symbol, Tree, Water


@dataclass
class Cell:
    row: int
    col: int
    symbol: Symbol
    sector_id: int
    sector_type: str = "FOREST"
    fire_level: float = 0.0
    burn_level: float = 0.0
    extinguish_level: float = 0.0
    patrolled: bool = False
    temperature: float = 22.0
    air_humidity: float = 45.0
    litter_moisture: float = 30.0
    co2: float = 420.0
    pm2_5: float = 8.0


class Grid:
    GRID_SIZE = 20
    DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    WIND_VECTOR = {
        "N": (-1, 0),
        "S": (1, 0),
        "W": (0, -1),
        "E": (0, 1),
    }

    def __init__(self, rows: int | None = None, columns: int | None = None):
        self.rows = rows or self.GRID_SIZE
        self.columns = columns or self.GRID_SIZE
        self.size = self.rows
        self.lock = RLock()
        self.grid = [
            [Cell(row, col, Tree(), sector_id=row * self.columns + col + 1) for col in range(self.columns)]
            for row in range(self.rows)
        ]
        self.wind_speed = 0.0
        self.wind_direction = "N"
        self.humidity = 45.0
        self.agents: dict[str, Agent] = {}
        self.rewrite_rules = FirePropagationRules()
        self.last_applied_rules: list[str] = []

    @classmethod
    def from_config(cls, config: dict | None) -> "Grid":
        config = config or {}
        rows = config.get("rows") or config.get("size") or cls.GRID_SIZE
        columns = config.get("columns") or config.get("size") or rows
        grid = cls(rows=int(rows), columns=int(columns))

        sectors = config.get("sectors") or []
        for sector in sectors:
            row = _coerce_int(sector.get("row"), 0)
            col = _coerce_int(sector.get("column") or sector.get("col"), 0)
            if _looks_one_indexed(sectors, rows, columns):
                row -= 1
                col -= 1
            initial_state = sector.get("initialState") or {}
            fire_level = float(initial_state.get("fireLevel") or 0.0)
            sector_type = str(sector.get("sectorType") or "TREE").upper()
            if grid.in_bounds(row, col):
                cell = grid[row, col]
                cell.sector_type = sector_type
                cell.temperature = float(initial_state.get("temperature") or cell.temperature)
                cell.air_humidity = float(initial_state.get("airHumidity") or initial_state.get("humidity") or cell.air_humidity)
                cell.litter_moisture = float(initial_state.get("plantLitterMoisture") or cell.litter_moisture)
                cell.co2 = float(initial_state.get("co2Concentration") or cell.co2)
                cell.pm2_5 = float(initial_state.get("pm2_5Concentration") or cell.pm2_5)
                if sector_type == "WATER":
                    cell.symbol = Water()
                if fire_level > 0:
                    grid.start_fire(row, col, fire_level=fire_level)

        if not sectors:
            center_row = grid.rows // 2
            center_col = grid.columns // 2
            grid.start_fire(center_row, center_col, fire_level=18.0)

        grid._load_agents(config)
        return grid

    def _load_agents(self, config: dict) -> None:
        brigades = config.get("fireBrigades") or []
        patrols = config.get("foresterPatrols") or []

        if not brigades:
            brigades = [
                {"fireBrigadeId": 1, "row": 0, "col": 0},
                {"fireBrigadeId": 2, "row": self.rows - 1, "col": self.columns - 1},
            ]
        if not patrols:
            patrols = [{"foresterPatrolId": 1, "row": self.rows - 1, "col": 0}]

        for brigade in brigades:
            agent_id = f"FB-{brigade.get('fireBrigadeId', brigade.get('id', len(self.agents) + 1))}"
            row, col = self._agent_start_position(brigade)
            self.agents[agent_id] = FireBrigade(agent_id, row, col)

        for patrol in patrols:
            agent_id = f"FP-{patrol.get('foresterPatrolId', patrol.get('id', len(self.agents) + 1))}"
            row, col = self._agent_start_position(patrol)
            self.agents[agent_id] = ForesterPatrol(agent_id, row, col)

    def _agent_start_position(self, payload: dict) -> tuple[float, float]:
        row = payload.get("row")
        col = payload.get("col") or payload.get("column")
        if row is not None and col is not None:
            return float(_clamp(int(row), 0, self.rows - 1)), float(_clamp(int(col), 0, self.columns - 1))

        location = payload.get("currentLocation") or payload.get("baseLocation") or payload.get("location")
        if location:
            return self.location_to_cell(location)

        return 0.0, 0.0

    def __iter__(self):
        return iter(self.grid)

    def __getitem__(self, position: tuple[int, int]) -> Cell:
        row, col = position
        return self.grid[row][col]

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.columns

    def location_to_cell(self, location: dict) -> tuple[float, float]:
        lat = float(location.get("latitude", 0.0))
        lon = float(location.get("longitude", 0.0))
        row = _clamp(round(abs(lat * 1000)) % self.rows, 0, self.rows - 1)
        col = _clamp(round(abs(lon * 1000)) % self.columns, 0, self.columns - 1)
        return float(row), float(col)

    def cell_to_location(self, row: int, col: int) -> dict:
        base_lat = 52.2297
        base_lon = 21.0122
        return {
            "latitude": round(base_lat + (row / max(self.rows - 1, 1)) * 0.08, 6),
            "longitude": round(base_lon + (col / max(self.columns - 1, 1)) * 0.08, 6),
        }

    def active_fires(self) -> list[dict]:
        fires = []
        for row in self.grid:
            for cell in row:
                if isinstance(cell.symbol, Fire):
                    fires.append(
                        {
                            "row": cell.row,
                            "col": cell.col,
                            "sectorId": cell.sector_id,
                            "sectorType": cell.sector_type,
                            "location": self.cell_to_location(cell.row, cell.col),
                            "fireLevel": round(cell.fire_level, 2),
                            "burnLevel": round(cell.burn_level, 2),
                        }
                    )
        return sorted(fires, key=lambda item: item["fireLevel"], reverse=True)

    def sensor_messages(self) -> list[tuple[str, dict]]:
        messages = []
        observed_cells = [fire for fire in self.active_fires()[:8]]
        if not observed_cells:
            center = self[self.rows // 2, self.columns // 2]
            observed_cells = [
                {
                    "row": center.row,
                    "col": center.col,
                    "sectorId": center.sector_id,
                    "sectorType": center.sector_type,
                    "location": self.cell_to_location(center.row, center.col),
                    "fireLevel": center.fire_level,
                    "burnLevel": center.burn_level,
                }
            ]

        for fire in observed_cells:
            cell = self[int(fire["row"]), int(fire["col"])]
            heat = float(fire["fireLevel"])
            smoke = max(0.0, heat * 1.8)
            sensor_base = f"S-{cell.sector_id}"
            common = {
                "sectorId": cell.sector_id,
                "sectorType": cell.sector_type,
                "location": self.cell_to_location(cell.row, cell.col),
            }
            messages.extend(
                [
                    (
                        "simulation.telemetry.sensors.temp_humidity",
                        {
                            **common,
                            "sensorId": f"{sensor_base}-TH",
                            "temperature": round(cell.temperature + heat * 0.45 + random.uniform(-0.5, 0.5), 2),
                            "temperatureUnit": "C",
                            "humidity": round(max(1.0, self.humidity - heat * 0.18 + random.uniform(-0.4, 0.4)), 2),
                            "humidityUnit": "%",
                        },
                    ),
                    (
                        "simulation.telemetry.sensors.wind_speed",
                        {**common, "sensorId": f"{sensor_base}-WS", "windSpeed": self.wind_speed, "windSpeedUnit": "m/s"},
                    ),
                    (
                        "simulation.telemetry.sensors.wind_direction",
                        {**common, "sensorId": f"{sensor_base}-WD", "windDirection": self.wind_direction, "windDirectionUnit": "cardinal"},
                    ),
                    (
                        "simulation.telemetry.sensors.litter_moisture",
                        {
                            **common,
                            "sensorId": f"{sensor_base}-LM",
                            "litterMoisture": round(max(0.0, cell.litter_moisture - heat * 0.12), 2),
                            "litterMoistureUnit": "%",
                        },
                    ),
                    (
                        "simulation.telemetry.sensors.co2",
                        {**common, "sensorId": f"{sensor_base}-CO2", "co2": round(cell.co2 + heat * 8.0, 2), "co2Unit": "ppm"},
                    ),
                    (
                        "simulation.telemetry.sensors.pm2_5",
                        {**common, "sensorId": f"{sensor_base}-PM25", "pm2_5": round(cell.pm2_5 + smoke, 2), "pm2_5Unit": "ug/m3"},
                    ),
                    (
                        "simulation.telemetry.sensors.camera",
                        {
                            **common,
                            "sensorId": f"{sensor_base}-CAM",
                            "smokeDetected": heat > 0,
                            "smokeLevel": round(smoke, 2),
                            "smokeLevelUnit": "index",
                            "fireVisible": heat > 5,
                        },
                    ),
                ]
            )
        return messages

    def sector_id_to_cell(self, sector_id: int | None) -> tuple[int, int] | None:
        if sector_id is None:
            return None
        index = int(sector_id) - 1
        row = index // self.columns
        col = index % self.columns
        if not self.in_bounds(row, col):
            return None
        return row, col

    def start_fire(self, row: int, col: int, fire_level: float | None = None) -> None:
        if not self.in_bounds(row, col):
            return
        cell = self[row, col]
        if isinstance(cell.symbol, (Tree, Fire)):
            cell.symbol = Fire()
            cell.fire_level = max(cell.fire_level, fire_level if fire_level is not None else random.uniform(8.0, 24.0))

    def extinguish(self, row: int, col: int, amount: float) -> bool:
        if not self.in_bounds(row, col):
            return True
        cell = self[row, col]
        cell.extinguish_level = max(cell.extinguish_level, amount)
        if not isinstance(cell.symbol, Fire):
            return True
        cell.fire_level = max(0.0, cell.fire_level - amount)
        if cell.fire_level <= 0.0:
            cell.symbol = Tree() if cell.burn_level < 85.0 else Burned()
            cell.extinguish_level = 0.0
            return True
        return False

    def mark_patrolled(self, row: int, col: int) -> None:
        if self.in_bounds(row, col):
            self[row, col].patrolled = True

    def get_neighbors(self, row: int, col: int) -> list[Cell]:
        neighbors = []
        for row_delta, col_delta in self.DIRECTIONS:
            neighbor_row = row + row_delta
            neighbor_col = col + col_delta
            if self.in_bounds(neighbor_row, neighbor_col):
                neighbors.append(self[neighbor_row, neighbor_col])
        return neighbors

    def step_fire(self) -> None:
        self.last_applied_rules = self.rewrite_rules.rewrite_grid(self)
        self._drift_environment()

    def _drift_environment(self) -> None:
        self.wind_speed = round(_clamp(self.wind_speed + random.uniform(-0.2, 0.3), 0.0, 40.0), 2)
        self.humidity = round(_clamp(self.humidity + random.uniform(-0.5, 0.5), 5.0, 95.0), 2)
        if random.random() < 0.03:
            self.wind_direction = random.choice(["N", "E", "S", "W"])

    def to_response(
        self,
        tick: int = 0,
        running: bool = False,
        simulation_session_id: str | None = None,
        messages: list[dict] | None = None,
    ) -> GridResponse:
        cells = []
        tree_count = 0
        fire_count = 0
        burned_count = 0

        for row in self.grid:
            for cell in row:
                if isinstance(cell.symbol, Tree):
                    tree_count += 1
                elif isinstance(cell.symbol, Fire):
                    fire_count += 1
                elif isinstance(cell.symbol, Burned):
                    burned_count += 1
                cells.append(
                    CellResponse(
                        row=cell.row,
                        col=cell.col,
                        symbol_type=cell.symbol.kind.value,
                        sector_id=cell.sector_id,
                        sector_type=cell.sector_type,
                        fire_level=round(cell.fire_level, 2),
                        burn_level=round(cell.burn_level, 2),
                        extinguish_level=round(cell.extinguish_level, 2),
                    )
                )

        return GridResponse(
            cells=cells,
            wind_speed=self.wind_speed,
            wind_direction=self.wind_direction,
            humidity=self.humidity,
            sectors=self._sector_overlays(),
            agents=[AgentResponse(**agent.to_response()) for agent in self.agents.values()],
            messages=[MessageResponse(**message) for message in (messages or [])],
            stats=SimulationStats(
                tick=tick,
                running=running,
                fire_count=fire_count,
                burned_count=burned_count,
                tree_count=tree_count,
                agent_count=len(self.agents),
                simulation_session_id=simulation_session_id,
            ),
        )

    def _sector_overlays(self) -> list[dict]:
        overlays = []
        sector_rows = 4
        sector_cols = 4
        row_step = max(1, self.rows // sector_rows)
        col_step = max(1, self.columns // sector_cols)

        sector_id = 1
        for row_from in range(0, self.rows, row_step):
            row_to = min(self.rows - 1, row_from + row_step - 1)
            for col_from in range(0, self.columns, col_step):
                col_to = min(self.columns - 1, col_from + col_step - 1)
                is_on_fire = any(
                    isinstance(self[row, col].symbol, Fire)
                    for row in range(row_from, row_to + 1)
                    for col in range(col_from, col_to + 1)
                )
                overlays.append(
                    {
                        "id": str(sector_id),
                        "row_from": row_from,
                        "row_to": row_to,
                        "col_from": col_from,
                        "col_to": col_to,
                        "is_on_fire": is_on_fire,
                    }
                )
                sector_id += 1

        return overlays


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _looks_one_indexed(sectors: list[dict], rows: int, columns: int) -> bool:
    row_values = [_coerce_int(sector.get("row"), 0) for sector in sectors]
    col_values = [_coerce_int(sector.get("column") or sector.get("col"), 0) for sector in sectors]
    return bool(row_values and col_values and (max(row_values) == rows or max(col_values) == columns))
