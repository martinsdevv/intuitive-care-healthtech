from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Trimestre:
    ano: int
    numero: int  # 1..4
