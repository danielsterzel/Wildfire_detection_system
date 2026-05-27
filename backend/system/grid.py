from dataclasses import dataclass
import random

from backend.system.symbols import Symbol, Tree, Fire, Burned, Water
from backend.system.schemas import CellResponse, GridResponse

@dataclass
class Cell:
    row: int
    col: int
    symbol: Symbol


class Grid:

    GRID_SIZE = 20
    DIRECTIONS = [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1)
    ]

    def __init__(self):

        self.size = self.GRID_SIZE
        self.grid = [[
            Cell(row, col, Tree()) for col in range(self.size)
        ]
            for row in range(self.size)
        ]
        # environmental parameters (defaults)
        self.wind_speed = 0.0
        self.wind_direction = "N"
        self.humidity = 50.0

    def __iter__(self):
        return iter(self.grid)

    def __getitem__(self, position: tuple[int, int]) -> Cell:

        row, col = position

        return self.grid[row][col]

    def start_fire(self, row: int, col: int):

        cell = self[row, col]

        if isinstance(cell.symbol, Tree):
            cell.symbol = Fire()

    def get_neighbors(self, row, col):
        neighbors = []

        for row_direction, col_direction in self.DIRECTIONS:
            neighbor_row = row + row_direction
            neighbor_col = col + col_direction

            if 0 <= neighbor_row < self.size and 0 <= neighbor_col < self.size:
                neighbors.append(self[neighbor_row, neighbor_col])

        return neighbors


    def rewrite(self, cell, neighbors):
        if isinstance(cell.symbol, Tree):
            has_fire_neighbor = any(
                isinstance(neighbor.symbol, Fire)
                for neighbor in neighbors
            )

            if has_fire_neighbor:
                # base probability
                base = 0.05
                # increase with wind speed (simple linear factor)
                wind_factor = 1.0 + min(self.wind_speed / 20.0, 2.0)
                # decrease with humidity
                humidity_factor = max(0.1, 1.0 - (self.humidity / 100.0))

                # check if any fire neighbor is in wind direction (crude mapping)
                dir_map = {(-1, 0): 'N', (1, 0): 'S', (0, -1): 'W', (0, 1): 'E'}
                wind_dir_char = self.wind_direction[0].upper() if self.wind_direction else 'N'
                favored = False
                for n in neighbors:
                    if isinstance(n.symbol, Fire):
                        dr = n.row - cell.row
                        dc = n.col - cell.col
                        if dir_map.get((dr, dc), '') == wind_dir_char:
                            favored = True
                            break

                wind_dir_factor = 1.5 if favored else 1.0

                prob = base * wind_factor * humidity_factor * wind_dir_factor
                if random.random() < prob:
                    return Fire()
        elif isinstance(cell.symbol, Fire):
            return Burned()

        return cell.symbol

    def to_response(self):
        cells = []

        for row in self.grid:
            for cell in row:
                cells.append(
                    CellResponse(
                        row=cell.row,
                        col=cell.col,
                        symbol_type=cell.symbol.kind
                    )
                )

        # build example sector covering center (for frontend visualization)
        sector_size = 5
        center = self.size // 2
        sec_row_from = max(0, center - sector_size // 2)
        sec_col_from = max(0, center - sector_size // 2)
        sec_row_to = min(self.size - 1, sec_row_from + sector_size - 1)
        sec_col_to = min(self.size - 1, sec_col_from + sector_size - 1)

        # determine if any cell in sector is on fire
        is_on_fire = False
        for r in range(sec_row_from, sec_row_to + 1):
            for c in range(sec_col_from, sec_col_to + 1):
                if isinstance(self[r, c].symbol, Fire):
                    is_on_fire = True
                    break
            if is_on_fire:
                break

        sector = {
            "id": "A",
            "row_from": sec_row_from,
            "row_to": sec_row_to,
            "col_from": sec_col_from,
            "col_to": sec_col_to,
            "is_on_fire": is_on_fire,
        }

        return GridResponse(cells=cells, wind_speed=self.wind_speed, wind_direction=self.wind_direction, humidity=self.humidity, sectors=[sector])
