from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class ExperienceRepository(ABC):

    @abstractmethod
    def create(
        self,
        experience_id: str,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: Optional[str],
    ) -> Dict:
        pass

    @abstractmethod
    def get(
        self,
        experience_id: str,
    ) -> Optional[Dict]:
        pass

    @abstractmethod
    def list_for_memory(
        self,
        bank_id: str,
        canonical_memory_id: int,
    ) -> List[Dict]:
        pass

    @abstractmethod
    def close(self):
        pass