import threading
import time
import random


class FallbackEnv(threading.Thread):
    """Simple environment simulator that updates grid.wind_speed, grid.wind_direction, grid.humidity.

    Runs in background when RabbitMQ is not available.
    """
    DIRECTIONS = ['N', 'E', 'S', 'W']

    def __init__(self, grid, interval: float = 1.0):
        super().__init__(daemon=True)
        self.grid = grid
        self.interval = interval
        self._stop = threading.Event()
        self._ws = float(getattr(grid, 'wind_speed', 0.0))
        self._hum = float(getattr(grid, 'humidity', 50.0))
        self._dir = getattr(grid, 'wind_direction', 'N') or 'N'

    def run(self):
        while not self._stop.is_set():
            # smooth random walk for wind speed
            self._ws += random.uniform(-0.6, 0.6)
            self._ws = max(0.0, min(self._ws, 40.0))

            # slow random walk for humidity
            self._hum += random.uniform(-1.5, 1.5)
            self._hum = max(0.0, min(self._hum, 100.0))

            # occasional direction change
            if random.random() < 0.12:
                self._dir = random.choice(self.DIRECTIONS)

            # apply to grid
            try:
                self.grid.wind_speed = round(self._ws, 2)
                self.grid.humidity = round(self._hum, 2)
                self.grid.wind_direction = self._dir
            except Exception:
                pass

            time.sleep(self.interval)

    def stop(self):
        self._stop.set()
