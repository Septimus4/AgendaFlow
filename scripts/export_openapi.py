import json
import sys
from pathlib import Path

# Add parent directory to path to import api module
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app


def export_openapi():
    """Export OpenAPI schema to JSON file."""
    openapi_schema = app.openapi()

    output_path = Path("docs/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI schema exported to {output_path}")


if __name__ == "__main__":
    export_openapi()
