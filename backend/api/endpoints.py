from fastapi import APIRouter
from backend.system.grid import Grid
from backend.system.simulation import Simulation
import os

router = APIRouter()

grid = Grid()
grid.start_fire(10, 10)
simulation = Simulation(grid)

# start rabbitmq consumer to keep environment params updated (best-effort)
consumer = None
try:
    # import inside try so missing pika doesn't break the API import
    from backend.system.rabbitmq_consumer import RabbitMQConsumer

    rabbit_url = os.environ.get('RABBITMQ_URL')
    queue = os.environ.get('RABBITMQ_STATE_QUEUE', 'simulation_state_queue')
    consumer = RabbitMQConsumer(grid, amqp_url=rabbit_url, queue_name=queue)
    consumer.start()
except Exception:
    # if pika not installed or connection fails, continue without consumer
    consumer = None

# if no rabbit consumer, start a lightweight fallback env simulator
try:
    if consumer is None:
        from backend.system.fallback_env import FallbackEnv

        fallback = FallbackEnv(grid)
        fallback.start()
    else:
        fallback = None
except Exception:
    fallback = None


@router.get("/grid")
def get_grid():
    simulation.tick()
    return simulation.grid.to_response()


