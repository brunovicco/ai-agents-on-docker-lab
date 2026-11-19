"""Schedule equal, independent one-hour charge blocks from synthetic telemetry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Forecast:
    """Grid draw in Wh for each eligible hour and the number to select."""

    grid: dict[int, int]
    slots: int

    @classmethod
    def parse(cls, data: object) -> "Forecast":
        """Validate a one-day forecast before computing incremental grid draw."""
        if not isinstance(data, dict):
            raise ValueError("Previsão inválida")
        charge, slots, rows = data.get("charge_wh"), data.get("slots"), data.get("hours")
        if type(charge) is not int or charge <= 0 or type(slots) is not int:
            raise ValueError("Carga e duração inválidas")
        if not isinstance(rows, list) or not 1 <= slots <= len(rows) <= 24:
            raise ValueError("Quantidade de horas inválida")
        grid: dict[int, int] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Linha inválida")
            hour, pv, home = row.get("hour"), row.get("pv_wh"), row.get("home_wh")
            if type(hour) is not int or not 0 <= hour < 24 or hour in grid:
                raise ValueError("Hora inválida ou duplicada")
            if type(pv) is not int or type(home) is not int or min(pv, home) < 0:
                raise ValueError("Energia inválida")
            grid[hour] = max(0, charge - max(0, pv - home))
        return cls(grid, slots)

    def propose(self) -> list[int]:
        """Choose lowest grid draw, breaking ties by earliest hour."""
        return sorted(sorted(self.grid, key=lambda h: (self.grid[h], h))[: self.slots])

    def verify(self, hours: object) -> int:
        """Check feasibility and optimality independently of the planner's sorting."""
        if not isinstance(hours, list) or len(hours) != self.slots:
            raise ValueError("Duração incorreta")
        if any(type(h) is not int or h not in self.grid for h in hours):
            raise ValueError("Hora fora da previsão")
        if len(set(hours)) != self.slots:
            raise ValueError("Hora repetida")
        cost = sum(self.grid[h] for h in hours)
        # Replacing any selected block by a cheaper unused block improves the plan.
        if any(self.grid[a] > self.grid[b] for a in hours for b in self.grid if b not in hours):
            raise ValueError("Existe horário com menor consumo da rede")
        return cost
