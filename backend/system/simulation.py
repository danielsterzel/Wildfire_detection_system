from backend.system.grid import Grid

class Simulation:

    def __init__(self, grid_arg: Grid | None = None):

        self.grid = grid_arg if grid_arg else Grid()

    def tick(self):

        next_symbols = []

        for row in range(self.grid.size):

            next_row = []

            for col in range(self.grid.size):
                cell = self.grid[row, col]

                neighbors = self.grid.get_neighbors(row, col)

                symbol = self.grid.rewrite(cell, neighbors)

                next_row.append(symbol)

            next_symbols.append(next_row)

        for row in range(self.grid.size):
            for col in range(self.grid.size):
                self.grid[row, col].symbol = next_symbols[row][col]


    def run_sim(self):
        pass

