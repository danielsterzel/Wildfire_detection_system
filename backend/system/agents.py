from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentTask:
    task_type: str
    target_row: Optional[int] = None
    target_col: Optional[int] = None
    sector_id: Optional[int] = None
    description: str = ""
    priority: int = 10


@dataclass
class Agent:
    agent_id: str
    type: str
    row: float
    col: float
    base_row: float
    base_col: float
    state: str = "AVAILABLE"
    speed: float = 0.22
    task: Optional[AgentTask] = None
    target_row: Optional[float] = None
    target_col: Optional[float] = None
    patrol_elapsed: float = 0.0
    completed_tasks: list[AgentTask] = field(default_factory=list)

    def assign(self, task: AgentTask) -> None:
        self.task = task
        if task.task_type == "return_to_base":
            self.target_row = self.base_row
            self.target_col = self.base_col
            self.state = "TRAVELLING"
            return

        self.target_row = float(task.target_row) if task.target_row is not None else self.row
        self.target_col = float(task.target_col) if task.target_col is not None else self.col
        self.state = "TRAVELLING"

    def update(self, grid, delta: float) -> dict:
        if self.state == "TRAVELLING":
            if self._move(delta):
                return self._on_arrival(grid)
            return {"event": "moving"}

        if self.state in {"EXTINGUISHING", "PATROLLING"}:
            return self._execute(grid, delta)

        return {"event": "idle"}

    def _move(self, delta: float) -> bool:
        if self.target_row is None or self.target_col is None:
            self.state = "AVAILABLE"
            return True

        row_diff = self.target_row - self.row
        col_diff = self.target_col - self.col
        distance = (row_diff * row_diff + col_diff * col_diff) ** 0.5
        if distance <= 0.01:
            self.row = self.target_row
            self.col = self.target_col
            return True

        step = min(distance, self.speed * delta)
        self.row += (row_diff / distance) * step
        self.col += (col_diff / distance) * step
        return False

    def _on_arrival(self, grid) -> dict:
        if not self.task or self.task.task_type == "return_to_base":
            self._complete_task()
            return {"event": "reached_base"}

        if self.task.task_type == "extinguish":
            self.state = "EXTINGUISHING"
            return {"event": "reached_fire"}

        if self.task.task_type == "patrol":
            self.state = "PATROLLING"
            self.patrol_elapsed = 0.0
            return {"event": "reached_patrol"}

        self._complete_task()
        return {"event": "task_complete"}

    def _execute(self, grid, delta: float) -> dict:
        if not self.task:
            self.state = "AVAILABLE"
            return {"event": "idle"}

        row = int(round(self.row))
        col = int(round(self.col))

        if self.state == "EXTINGUISHING":
            is_done = grid.extinguish(row, col, amount=7.5 * delta)
            if is_done:
                self._complete_task()
                return {"event": "fire_extinguished"}
            return {"event": "extinguishing"}

        if self.state == "PATROLLING":
            self.patrol_elapsed += delta
            grid.mark_patrolled(row, col)
            if self.patrol_elapsed >= 8.0:
                self._complete_task()
                return {"event": "patrol_complete"}
            return {"event": "patrolling"}

        return {"event": "idle"}

    def _complete_task(self) -> None:
        if self.task:
            self.completed_tasks.append(self.task)
        self.task = None
        self.target_row = None
        self.target_col = None
        self.state = "AVAILABLE"

    def to_response(self) -> dict:
        row = max(0, int(round(self.row)))
        col = max(0, int(round(self.col)))
        return {
            "agent_id": self.agent_id,
            "type": self.type,
            "row": self.row,
            "col": self.col,
            "state": self.state,
            "target_row": int(round(self.target_row)) if self.target_row is not None else None,
            "target_col": int(round(self.target_col)) if self.target_col is not None else None,
            "sector_id": None,
        }


class FireBrigade(Agent):
    def __init__(self, agent_id: str, row: float, col: float):
        super().__init__(
            agent_id=agent_id,
            type="fire_brigade",
            row=row,
            col=col,
            base_row=row,
            base_col=col,
            speed=0.35,
        )


class ForesterPatrol(Agent):
    def __init__(self, agent_id: str, row: float, col: float):
        super().__init__(
            agent_id=agent_id,
            type="forester",
            row=row,
            col=col,
            base_row=row,
            base_col=col,
            speed=0.28,
        )
