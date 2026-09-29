from hindsight_client import Hindsight

from app.core.config import settings


class HindsightClient:
    def __init__(self):
        if not settings.HINDSIGHT_API_KEY:
            raise RuntimeError(
                "HINDSIGHT_API_KEY is not configured"
            )

        self.client = Hindsight(
            base_url=settings.HINDSIGHT_BASE_URL,
            api_key=settings.HINDSIGHT_API_KEY,
        )

    def close(self):
        self.client.close()