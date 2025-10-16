import uuid
from pathlib import Path


class TablePlugin:
    """Modular table rendering for directives."""

    @staticmethod
    def render_table(data: dict, table_id: str | None = None) -> str:
        if not table_id:
            table_id = f"data-table-{uuid.uuid4().hex[:8]}"  # Unique for multi

        if isinstance(data, str):  # File load
            file_path = Path(data)
            if file_path.stat().st_size > 1_000_000:  # 1MB threshold
                raise ValueError("File too large for table")
            # Load and parse

        # Generate HTML with unique ID
        return f'<div class="bengal-data-table-wrapper" data-table-id="{table_id}">...</div>'

    def validate_size(self, file_path: Path) -> bool:
        return file_path.stat().st_size <= 1_000_000
