import os
from pathlib import Path


class StorageConfig:
    """
    Central storage configuration.

    DEVELOPMENT:
        STORAGE_BACKEND=sqlite

    DEPLOYMENT:
        STORAGE_BACKEND=postgres
        DATABASE_URL=postgresql://...

    The application services do not depend on this directly.
    They receive repository implementations through the factory.
    """

    def __init__(self):
        self.backend = os.getenv(
            "STORAGE_BACKEND",
            "sqlite",
        ).strip().lower()

        self.sqlite_path = Path(
            os.getenv(
                "LEARNING_DATABASE_PATH",
                "memory_learning.db",
            )
        )

        self.database_url = os.getenv(
            "DATABASE_URL",
            "",
        ).strip()

        if self.backend not in {"sqlite", "postgres"}:
            raise ValueError(
                "STORAGE_BACKEND must be either 'sqlite' or 'postgres'."
            )

        if self.backend == "postgres" and not self.database_url:
            raise RuntimeError(
                "DATABASE_URL is required when STORAGE_BACKEND=postgres."
            )


settings = StorageConfig()