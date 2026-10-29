import json

from supportdesk.config import project_root
from supportdesk.main import create_app
from supportdesk.modules.realtime.protocol import RealtimeFrame


def export() -> None:
    root = project_root()
    for filename, schema in [
        ("openapi.json", create_app().openapi()),
        ("realtime.schema.json", RealtimeFrame.model_json_schema()),
    ]:
        (root / "contracts" / filename).write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n"
        )


if __name__ == "__main__":
    export()
