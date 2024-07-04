from __future__ import annotations

from meilisearch_python_sdk import AsyncClient


DEFAULT_TIMEOUT = 10

class MeiliSearchClient(AsyncClient):
    """An asynchronous MeiliSearch client."""

    @staticmethod
    def from_host(
        host: str,
        port: int,
        api_key: str | None = None,
        *,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> MeiliSearchClient:
        return MeiliSearchClient(
            f"http://{host}:{port}",
            api_key,
            timeout=timeout,
        )
