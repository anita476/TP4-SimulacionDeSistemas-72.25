from pathlib import Path

def find_executable(root: Path, name: str, dirs: tuple[str, ...] = ("build", "build-local")) -> Path:
    """Locate a CMkae-build binary under root, with or without the Windows .exe suffix"""
    for folder in dirs:
        for candidate in (root / folder / name, root / folder / f"{name}.exe"):
            if candidate.is_file():
                return candidate
    searched = ", ".join(str(root / folder) for folder in dirs)
    raise FileNotFoundError(f"{name} not found under {searched}; build it first (cmake --build build)")
    