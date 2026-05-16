import yaml
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(config_path="config/params.yaml"):
    """Load configuration from a YAML file.

    Paths are resolved relative to the project root, not the
    current working directory, so the pipeline works from any cwd.
    """
    path = _PROJECT_ROOT / config_path
    if not path.exists():
        raise FileNotFoundError(f"Config file not found at: {path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config
