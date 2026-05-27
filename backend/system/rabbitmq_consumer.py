import threading
import json
import os
import time

import pika


class RabbitMQConsumer(threading.Thread):
    def __init__(self, grid, amqp_url=None, queue_name='simulation_state_queue'):
        super().__init__(daemon=True)
        self.grid = grid
        self.queue_name = queue_name
        self._stop = threading.Event()
        self.amqp_url = amqp_url or os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/%2F')

    def run(self):
        params = pika.URLParameters(self.amqp_url)
        while not self._stop.is_set():
            try:
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.queue_declare(queue=self.queue_name, durable=True)

                for method, properties, body in channel.consume(self.queue_name, inactivity_timeout=1):
                    if self._stop.is_set():
                        break
                    if body is None:
                        continue
                    try:
                        data = json.loads(body)
                    except Exception:
                        continue

                    # expect snapshot with environment
                    env = data.get('environment') if isinstance(data, dict) else None
                    if env:
                        # update grid environment safely
                        try:
                            ws = env.get('windSpeed') or env.get('wind_speed')
                            wd = env.get('windDirection') or env.get('wind_direction')
                            hum = env.get('humidity')

                            if ws is not None:
                                try:
                                    self.grid.wind_speed = float(ws)
                                except Exception:
                                    pass

                            if wd is not None:
                                self.grid.wind_direction = str(wd)

                            if hum is not None:
                                try:
                                    self.grid.humidity = float(hum)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                try:
                    channel.cancel()
                    connection.close()
                except Exception:
                    pass

            except Exception:
                # reconnect after short delay
                time.sleep(2)

    def stop(self):
        self._stop.set()
