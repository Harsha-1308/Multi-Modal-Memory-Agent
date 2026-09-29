from app.storage.storage_config import settings

from app.repositories.sqlite.learning_repository import (
    SQLiteLearningRepository,
)


def create_learning_repository():

    if settings.backend == "sqlite":

        return SQLiteLearningRepository(
            db_path=str(
                settings.sqlite_path
            )
        )

    if settings.backend == "postgres":

        raise NotImplementedError(
            "PostgreSQL repository is intentionally "
            "not enabled yet. The repository boundary "
            "is ready; the PostgreSQL adapter will be "
            "added before deployment."
        )

    raise RuntimeError(
        f"Unsupported storage backend: "
        f"{settings.backend}"
    )