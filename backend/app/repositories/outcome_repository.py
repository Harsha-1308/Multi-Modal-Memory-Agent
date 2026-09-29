from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class OutcomeRepository(ABC):

    @abstractmethod
    def create(
        self,
        outcome_id: str,
        experience_id: str,
        outcome_type: str,
        summary: str,
        details: Optional[str],
    ) -> Dict:
        pass

    @abstractmethod
    def get(
        self,
        outcome_id: str,
    ) -> Optional[Dict]:
        pass

    @abstractmethod
    def list_for_experience(
        self,
        experience_id: str,
    ) -> List[Dict]:
        pass

    @abstractmethod
    def close(self):
        pass