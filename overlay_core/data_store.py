import csv
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import ProcessSpec


TEAM_DATE_BOUNDS = {
    "green": ("20200810", "20200820"),
    "pink": ("20200821", "20200924"),
}


class DataStore:
    """Local dataset accessor responsible for enforcing team-specific slices."""

    def __init__(
        self,
        process_id: str,
        team: str,
        dataset_root: str = "datasets/2020-fire/data",
        date_bounds: Optional[Tuple[str, str]] = None,
        team_members: Optional[Sequence["ProcessSpec"]] = None,
    ):
        self.process_id = process_id
        self.team = team.lower()
        self.dataset_root = Path(dataset_root)
        self._records: List[Dict[str, object]] = []
        self._files_loaded = 0
        self._explicit_bounds = date_bounds
        self._team_members = list(team_members or [])
        self._load()

    @property
    def records_loaded(self) -> int:
        return len(self._records)

    @property
    def files_loaded(self) -> int:
        return self._files_loaded

    def _load(self) -> None:
        if not self.dataset_root.exists():
            raise FileNotFoundError(f"Dataset root missing: {self.dataset_root}")

        bounds = TEAM_DATE_BOUNDS.get(self.team)
        if not bounds:
            raise ValueError(f"Unknown team '{self.team}' for datastore.")

        date_directories: List[Tuple[str, Path]] = []
        lower, upper = bounds
        for date_dir in sorted(self.dataset_root.iterdir()):
            if not date_dir.is_dir():
                continue
            date_str = date_dir.name
            if lower <= date_str <= upper:
                date_directories.append((date_str, date_dir))

        selected_dates = self._resolve_selected_dates([date for date, _ in date_directories])

        for date_str, date_dir in date_directories:
            if selected_dates and date_str not in selected_dates:
                continue
            for csv_file in sorted(date_dir.glob("*.csv")):
                self._load_file(csv_file, date_str)

        print(f"[DataStore] {self.process_id} loaded {self.records_loaded} rows from {self.files_loaded} files.", flush=True)

    def _load_file(self, path: Path, date_str: str) -> None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if not row or row[0].strip('"').lower() == "latitude":
                        continue
                    record = self._convert_row(row, date_str)
                    if record:
                        self._records.append(record)
            self._files_loaded += 1
        except Exception as exc:
            print(f"[DataStore] failed to load {path}: {exc}", flush=True)

    @staticmethod
    def _convert_row(row: List[str], date_str: str) -> Optional[Dict[str, object]]:
        try:
            return {
                "latitude": float(row[0].strip('"')),
                "longitude": float(row[1].strip('"')),
                "timestamp": row[2].strip('"'),
                "parameter": row[3].strip('"'),
                "value": float(row[4].strip('"')) if row[4].strip('"') else 0.0,
                "unit": row[5].strip('"'),
                "aqi": int(row[7].strip('"')) if len(row) > 7 and row[7].strip('"') else 0,
                "site_name": row[9].strip('"') if len(row) > 9 else "",
                "date": date_str,
            }
        except (ValueError, IndexError):
            return None

    def query(self, filters: Dict[str, object], limit: Optional[int] = None) -> List[Dict[str, object]]:
        """Return dataset rows that match filters up to limit."""
        remaining = limit or filters.get("limit")
        remaining = int(remaining) if remaining else len(self._records)
        remaining = max(1, remaining)

        results: List[Dict[str, object]] = []
        for record in self._records:
            if self._matches(record, filters):
                results.append(record)
                if len(results) >= remaining:
                    break
        return results

    @staticmethod
    def _matches(record: Dict[str, object], filters: Dict[str, object]) -> bool:
        parameter = filters.get("parameter")
        if parameter and str(record["parameter"]).lower() != str(parameter).lower():
            return False

        min_val = filters.get("min_value")
        if min_val is not None and record["value"] < float(min_val):
            return False

        max_val = filters.get("max_value")
        if max_val is not None and record["value"] > float(max_val):
            return False

        date_start = filters.get("date_start")
        if date_start and str(record["date"]) < str(date_start):
            return False

        date_end = filters.get("date_end")
        if date_end and str(record["date"]) > str(date_end):
            return False

        lat_min = filters.get("lat_min")
        if lat_min is not None and record["latitude"] < float(lat_min):
            return False

        lat_max = filters.get("lat_max")
        if lat_max is not None and record["latitude"] > float(lat_max):
            return False

        lon_min = filters.get("lon_min")
        if lon_min is not None and record["longitude"] < float(lon_min):
            return False

        lon_max = filters.get("lon_max")
        if lon_max is not None and record["longitude"] > float(lon_max):
            return False

        return True

    def stats(self) -> Dict[str, int]:
        return {
            "records": self.records_loaded,
            "files": self.files_loaded,
        }

    def _resolve_selected_dates(self, all_dates: List[str]) -> Optional[Set[str]]:
        if not all_dates:
            return set()

        if self._explicit_bounds:
            lower, upper = self._explicit_bounds
            return {date for date in all_dates if lower <= date <= upper}

        if not self._team_members:
            return None

        team_members = [
            member for member in self._team_members if member.team.lower() == self.team
        ]
        if not team_members:
            return None

        member_ids = [member.id for member in team_members]
        if self.process_id not in member_ids:
            return None

        shares = self._compute_member_shares(team_members, len(all_dates))
        start = 0
        selected: Set[str] = set()
        for idx, member in enumerate(team_members):
            share = shares[idx]
            end = min(len(all_dates), start + share)
            if idx == len(team_members) - 1:
                end = len(all_dates)
            if member.id == self.process_id:
                selected.update(all_dates[start:end])
            start = end
        return selected or None

    def _compute_member_shares(self, members: Sequence["ProcessSpec"], total_dates: int) -> List[int]:
        if total_dates <= 0:
            return [0 for _ in members]

        role_weights = {"team_leader": 1, "worker": 2}
        weights = [role_weights.get(member.role, 1) for member in members]
        weight_total = sum(weights) or len(members)
        raw_shares = [
            max(1, int(round((weight / weight_total) * total_dates))) for weight in weights
        ]

        diff = total_dates - sum(raw_shares)
        if diff > 0:
            raw_shares[-1] += diff
        elif diff < 0 and raw_shares:
            take = min(raw_shares[-1] - 1, abs(diff))
            if take > 0:
                raw_shares[-1] -= take
        return raw_shares

