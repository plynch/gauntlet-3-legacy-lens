from collections.abc import Sequence

import httpx

from app.services.types import SearchHit, SourceChunk


class QdrantGateway:
    def __init__(self, base_url: str, api_key: str | None = None, timeout_seconds: float = 30.0) -> None:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["api-key"] = api_key

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers=headers,
        )

    def close(self) -> None:
        self._client.close()

    def ensure_collection(self, collection_name: str, vector_size: int) -> None:
        response = self._client.get(f"/collections/{collection_name}")
        if response.status_code == 200:
            return
        if response.status_code != 404:
            raise RuntimeError(f"Failed to inspect collection: {response.status_code} {response.text}")

        create_response = self._client.put(
            f"/collections/{collection_name}",
            json={"vectors": {"size": vector_size, "distance": "Cosine"}},
        )
        self._raise_for_error(create_response, "create collection")

    def has_matching_file_hash(self, collection_name: str, source_path: str, file_hash: str) -> bool:
        payload = self._scroll_one_by_path(collection_name, source_path)
        if payload is None:
            return False
        return payload.get("file_hash") == file_hash

    def delete_points_for_source_path(self, collection_name: str, source_path: str) -> None:
        response = self._client.post(
            f"/collections/{collection_name}/points/delete?wait=true",
            json={"filter": {"must": [{"key": "source_path", "match": {"value": source_path}}]}},
        )
        self._raise_for_error(response, "delete old points")

    def upsert_points(self, collection_name: str, chunks: Sequence[SourceChunk], vectors: Sequence[list[float]]) -> None:
        points = [
            {"id": chunk.id, "vector": vector, "payload": chunk_payload(chunk)}
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        response = self._client.put(
            f"/collections/{collection_name}/points?wait=true",
            json={"points": points},
        )
        self._raise_for_error(response, "upsert points")

    def search(self, collection_name: str, vector: list[float], limit: int) -> list[SearchHit]:
        response = self._client.post(
            f"/collections/{collection_name}/points/search",
            json={"vector": vector, "limit": limit, "with_payload": True},
        )
        self._raise_for_error(response, "search points")

        data = response.json()
        result_items = data.get("result", [])

        hits: list[SearchHit] = []
        for item in result_items:
            payload = item.get("payload", {})
            text = str(payload.get("text", ""))
            if not text:
                continue

            hits.append(
                SearchHit(
                    text=text,
                    score=float(item.get("score", 0.0)),
                    source_path=str(payload.get("source_path", "")),
                    line_start=int(payload.get("line_start", 1)),
                    line_end=int(payload.get("line_end", 1)),
                    section=str(payload.get("section")) if payload.get("section") is not None else None,
                )
            )

        return hits

    def _scroll_one_by_path(self, collection_name: str, source_path: str) -> dict | None:
        response = self._client.post(
            f"/collections/{collection_name}/points/scroll",
            json={
                "limit": 1,
                "with_payload": True,
                "with_vector": False,
                "filter": {"must": [{"key": "source_path", "match": {"value": source_path}}]},
            },
        )
        if response.status_code == 404:
            return None
        self._raise_for_error(response, "scroll points")
        data = response.json()
        points = data.get("result", {}).get("points", [])
        if not points:
            return None
        return points[0].get("payload", {})

    @staticmethod
    def _raise_for_error(response: httpx.Response, action: str) -> None:
        if response.is_success:
            return
        raise RuntimeError(f"Failed to {action}: {response.status_code} {response.text}")


def chunk_payload(chunk: SourceChunk) -> dict[str, str | int | None]:
    return {
        "text": chunk.text,
        "source_path": chunk.source_path,
        "file_hash": chunk.file_hash,
        "line_start": chunk.line_start,
        "line_end": chunk.line_end,
        "section": chunk.section,
    }
