from dataclasses import dataclass
from enum import Enum

#potem wiatr humidity i tak dalej

class SymbolEnum(str, Enum):
    TREE = "TREE"
    FIRE = "FIRE"
    BURNED = "BURNED"
    WATER = "WATER"

@dataclass
class Symbol:
    kind: SymbolEnum


@dataclass
class Tree(Symbol):
    kind :SymbolEnum = SymbolEnum.TREE
    flammability: float = 1.0

@dataclass
class Fire(Symbol):
    kind: SymbolEnum = SymbolEnum.FIRE
    intensity: float = 1.0

@dataclass
class Burned(Symbol):
    kind: SymbolEnum = SymbolEnum.BURNED
    pass


@dataclass
class Water(Symbol):
    kind: SymbolEnum = SymbolEnum.WATER
    pass

