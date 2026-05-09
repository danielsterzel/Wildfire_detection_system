from fastapi import APIRouter
from backend.system.grid import Grid
from backend.system.simulation import Simulation

router = APIRouter()

grid = Grid()
grid.start_fire(10, 10)
simulation = Simulation(grid)


@router.get("/grid")
def get_grid():
    simulation.tick()
    return simulation.grid.to_response()


