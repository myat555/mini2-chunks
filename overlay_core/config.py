import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class ProcessSpec:
    """Immutable description of a configured process in the overlay."""

    id: str
    role: str
    team: str
    host: str
    port: int
    neighbors: List[str]

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


class OverlayConfig:
    """Config facade that hides JSON parsing and lookup semantics."""

    def __init__(self, config_path: str):
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)

        processes = payload.get("processes", {})
        if not processes:
            raise ValueError("Configuration must include at least one process definition.")

        self._processes: Dict[str, ProcessSpec] = {}
        for pid, spec in processes.items():
            try:
                self._processes[pid] = ProcessSpec(
                    id=spec["id"],
                    role=spec["role"],
                    team=spec["team"],
                    host=spec["host"],
                    port=int(spec["port"]),
                    neighbors=list(spec.get("neighbors", [])),
                )
            except KeyError as exc:
                missing = exc.args[0]
                raise ValueError(f"Process '{pid}' missing required field '{missing}'.") from exc

    def get(self, process_id: str) -> ProcessSpec:
        if process_id not in self._processes:
            raise KeyError(f"Process '{process_id}' is not defined in the configuration.")
        return self._processes[process_id]

    def neighbors_of(self, process_id: str) -> List[ProcessSpec]:
        process = self.get(process_id)
        return [self.get(nid) for nid in process.neighbors if nid in self._processes]

    def all_processes(self) -> Dict[str, ProcessSpec]:
        return dict(self._processes)

