from pathlib import Path


def load_table(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if header is None:
                header = parts
                missing = [key for key in required if key not in header]
                if missing:
                    raise ValueError(f"{path}: expected columns {' '.join(required)}")
                continue
            raw = dict(zip(header, parts))
            missing = [key for key in required if not raw.get(key)]
            if missing:
                raise ValueError(f"{path}: missing {', '.join(missing)}")
            rows.append({key: raw[key] for key in required})
    if not rows:
        raise ValueError(f"{path}: no data rows")
    return rows
