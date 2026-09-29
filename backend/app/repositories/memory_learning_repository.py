from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class MemoryLearningRepository(ABC):

    @abstractmethod
    def refresh_learning_state(
        self,
        memory_id: int,
    ) -> Dict:
        pass

    @abstractmethod
    def get_learning_state(
        self,
        memory_id: int,
    ) -> Optional[Dict]:
        pass

    @abstractmethod
    def get_learning_provenance(
        self,
        memory_id: int,
    ) -> Optional[Dict]:
        pass

    @abstractmethod
    def close(self):
        pass