from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from typing import Any

try:
    import pika
except Exception:  # pragma: no cover - optional runtime dependency
    pika = None


class RabbitMQPublisher:
    def __init__(self, amqp_url: str | None = None, exchange: str | None = None):
        self.amqp_url = amqp_url or os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")
        self.exchange = exchange or os.environ.get("RABBITMQ_EXCHANGE", "wildfire.simulation")
        self.enabled = os.environ.get("RABBITMQ_ENABLED", "true").lower() != "false"
        self.status = "disabled" if not self.enabled else "starting"
        self._queue: deque[tuple[str, dict[str, Any]]] = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        if self.enabled and pika is not None:
            self._thread = threading.Thread(target=self._run, daemon=True, name="RabbitMQPublisher")
            self._thread.start()
        elif pika is None:
            self.status = "pika_missing"

    def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        if not self.enabled or pika is None:
            return
        with self._lock:
            self._queue.append((routing_key, payload))

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        connection = None
        channel = None

        while not self._stop.is_set():
            try:
                if connection is None or connection.is_closed:
                    connection = pika.BlockingConnection(pika.URLParameters(self.amqp_url))
                    channel = connection.channel()
                    channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=False)
                    self.status = "connected"

                item = None
                with self._lock:
                    if self._queue:
                        item = self._queue.popleft()

                if item is None:
                    time.sleep(0.1)
                    continue

                routing_key, payload = item
                channel.basic_publish(
                    exchange=self.exchange,
                    routing_key=routing_key,
                    body=json.dumps(payload),
                    properties=pika.BasicProperties(delivery_mode=1),
                )
            except Exception as exc:
                self.status = f"disconnected: {type(exc).__name__}"
                try:
                    if connection and not connection.is_closed:
                        connection.close()
                except Exception:
                    pass
                connection = None
                channel = None
                time.sleep(2.0)

        try:
            if connection and not connection.is_closed:
                connection.close()
        except Exception:
            pass
