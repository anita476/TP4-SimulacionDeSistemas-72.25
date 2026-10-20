import os
from pathlib import Path

def find_executable(root: Path, name: str, dirs: tuple[str, ...] = ("build", "build-local")) -> Path:
    """Locate a CMake-build binary under root, with or without the Windows .exe suffix"""
    names = (f"{name}.exe", name) if os.name == "nt" else (name, f"{name}.exe")
    for folder in dirs:
        for candidate_name in names:
            candidate = root / folder / candidate_name
            if candidate.is_file():
                return candidate
    searched = ", ".join(str(root / folder) for folder in dirs)
    raise FileNotFoundError(f"{name} not found under {searched}; build it first (cmake --build build)")
    