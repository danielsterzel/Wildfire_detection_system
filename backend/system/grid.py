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

            # to musimy zmieinc jak bedziemy mieli wiatr wilgoc i tak dalej
            if has_fire_neighbor and random.random() < 0.3:
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

        return GridResponse(cells=cells)
