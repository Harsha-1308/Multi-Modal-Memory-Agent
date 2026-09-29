from app.storage.repository_factory import create_learning_repository


class MemoryLearningStateService:

    def __init__(self, repository=None):

        self.repository = (
            repository
            if repository is not None
            else create_learning_repository()
        )

    def learn(
        self,
        canonical_memory_id: int,
    ):
        return self.repository.refresh_memory_learning_state(
            canonical_memory_id=canonical_memory_id
        )

    def refresh(
        self,
        canonical_memory_id: int,
    ):
        return self.learn(
            canonical_memory_id
        )

    def get_state(
        self,
        canonical_memory_id: int,
    ):
        return self.repository.get_memory_learning_state(
            canonical_memory_id=canonical_memory_id
        )

    def get_provenance(
        self,
        canonical_memory_id: int,
    ):
        return self.repository.get_memory_learning_provenance(
            canonical_memory_id=canonical_memory_id
        )

    def get_learning_view(
        self,
        canonical_memory_id: int,
    ):
        state = self.get_state(
            canonical_memory_id
        )

        if state is None:
            return None

        return {
            "memory_id": canonical_memory_id,
            "learning_state": state,
            "provenance": self.get_provenance(
                canonical_memory_id
            ),
        }

    def close(self):
        self.repository.close()