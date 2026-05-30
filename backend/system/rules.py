from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Protocol, TYPE_CHECKING

from backend.system.symbols import Burned, Fire, Tree

if TYPE_CHECKING:
    from backend.system.grid import Cell, Grid


@dataclass
class RewriteContext:
    grid: "Grid"
    cell: "Cell"
    neighbors: list["Cell"]


@dataclass
class RewriteResult:
    next_fires: list[tuple[int, int, float]] = field(default_factory=list)
    applied_rules: list[str] = field(default_factory=list)


class RewriteRule(Protocol):
    name: str
    production: str

    def apply(self, context: RewriteContext) -> RewriteResult:
        ...


class FireGrowthRule:
    name = "fire-growth"
    production = "FIRE(level,burn) -> FIRE(level+growth,burn+damage)"

    def apply(self, context: RewriteContext) -> RewriteResult:
        cell = context.cell
        if not isinstance(cell.symbol, Fire):
            return RewriteResult()

        growth = max(0.15, cell.fire_level * 0.04)
        cell.fire_level = min(100.0, cell.fire_level + growth)
        cell.burn_level = min(100.0, cell.burn_level + (cell.fire_level**2) * 0.002)
        return RewriteResult(applied_rules=[self.name])


class BurnoutRule:
    name = "burnout"
    production = "FIRE(burn>=100) -> BURNED"

    def apply(self, context: RewriteContext) -> RewriteResult:
        cell = context.cell
        if not isinstance(cell.symbol, Fire) or cell.burn_level < 100.0:
            return RewriteResult()

        cell.symbol = Burned()
        cell.fire_level = 0.0
        return RewriteResult(applied_rules=[self.name])


class FireSpreadRule:
    name = "fire-spread"
    production = "TREE + adjacent FIRE + environment -> FIRE"

    def apply(self, context: RewriteContext) -> RewriteResult:
        source = context.cell
        if not isinstance(source.symbol, Fire):
            return RewriteResult()

        result = RewriteResult()
        for neighbor in context.neighbors:
            if isinstance(neighbor.symbol, Tree) and random.random() < self.spread_probability(context.grid, source, neighbor):
                result.next_fires.append((neighbor.row, neighbor.col, random.uniform(6.0, 16.0)))

        if result.next_fires:
            result.applied_rules.append(self.name)
        return result

    def spread_probability(self, grid: "Grid", source: "Cell", target: "Cell") -> float:
        base = 0.025 + min(source.fire_level / 1000.0, 0.12)
        terrain_factor = {
            "WATER": 0.0,
            "MEADOW": 0.8,
            "GRASS": 0.9,
            "TREE": 1.15,
            "FOREST": 1.2,
            "CONIFEROUS": 1.35,
        }.get(target.sector_type.upper(), 1.0)
        humidity_factor = max(0.15, 1.0 - grid.humidity / 100.0)
        wind_speed_factor = 1.0 + min(grid.wind_speed / 35.0, 1.5)
        wind_vector = grid.WIND_VECTOR.get(str(grid.wind_direction).upper()[:1], (-1, 0))
        spread_vector = (target.row - source.row, target.col - source.col)
        wind_direction_factor = 1.7 if spread_vector == wind_vector else 0.9
        patrol_factor = 0.65 if target.patrolled else 1.0
        return min(0.75, base * terrain_factor * humidity_factor * wind_speed_factor * wind_direction_factor * patrol_factor)


class FirePropagationRules:
    """
    Local rewriting system inspired by formal production systems.

    Instead of rewriting a global string like a classical Lindenmayer system,
    this engine rewrites grid-cell states using local productions and
    neighborhood/environment context.
    """

    def __init__(self):
        self.rules: list[RewriteRule] = [
            FireGrowthRule(),
            BurnoutRule(),
            FireSpreadRule(),
        ]

    @property
    def productions(self) -> list[str]:
        return [f"{rule.name}: {rule.production}" for rule in self.rules]

    def rewrite_grid(self, grid: "Grid") -> list[str]:
        next_fires: list[tuple[int, int, float]] = []
        applied_rules: list[str] = []

        for row in range(grid.rows):
            for col in range(grid.columns):
                context = RewriteContext(
                    grid=grid,
                    cell=grid[row, col],
                    neighbors=grid.get_neighbors(row, col),
                )

                for rule in self.rules:
                    result = rule.apply(context)
                    next_fires.extend(result.next_fires)
                    applied_rules.extend(result.applied_rules)

        for row, col, fire_level in next_fires:
            grid.start_fire(row, col, fire_level)

        return applied_rules
