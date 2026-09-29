from app.integrations.hindsight_client import HindsightClient


class MemoryService:
    def __init__(self):
        self.hindsight = HindsightClient()

    def create_project_bank(
        self,
        bank_id: str,
        project_name: str,
        project_description: str,
    ):
        return self.hindsight.client.create_bank(
            bank_id=bank_id,
            name=project_name,
            background=project_description,
        )

    def retain(
        self,
        bank_id: str,
        content: str,
    ):
        return self.hindsight.client.retain(
            bank_id=bank_id,
            content=content,
        )

    def recall(self, bank_id: str, query: str, types=None):
        if types is None:
            types = [
            "world",
            "experience",
            "observation",
        ]

        return self.hindsight.client.recall(
        bank_id=bank_id,
        query=query,
        types=types,
        prefer_observations=True,

        # IMPORTANT:
        # When Hindsight returns a synthesized observation,
        # ask it to return the original contributing facts too.
        include_source_facts=True,
        max_source_facts_tokens=-1,

        budget="mid",
    )

    def reflect(
        self,
        bank_id: str,
        query: str,
    ):
        return self.hindsight.client.reflect(
            bank_id=bank_id,
            query=query,
        )

    def list_memories(
        self,
        bank_id: str,
        limit: int = 50,
    ):
        return self.hindsight.client.list_memories(
            bank_id=bank_id,
            limit=limit,
            offset=0,
        )

    def close(self):
        self.hindsight.close()