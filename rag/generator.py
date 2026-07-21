import requests

from rag.config import OLLAMA_HOST, OLLAMA_MODEL, SYSTEM_PROMPT


class OllamaGenerator:
    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.host = host.rstrip("/")
        self.model = model
        self.api_url = f"{self.host}/api/chat"

    def _build_messages(self, query: str, context_chunks: list[dict]) -> list[dict]:
        context_parts = []
        for i, chunk in enumerate(context_chunks):
            source = chunk.get("source", "Sconosciuto")
            section = chunk.get("section", "")
            loc = f"{source}"
            if section:
                loc += f" - {section}"
            context_parts.append(f"[{i + 1}] ({loc})\n{chunk['text']}")

        context_text = "\n\n".join(context_parts)

        user_msg = f"""Contesto dai manuali di Pathfinder 2e:

{context_text}

---

Domanda: {query}

Rispondi basandoti sul contesto fornito. Se la risposta non è nel contesto, dillo chiaramente. Cita le fonti quando possibile."""

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

    def generate(self, query: str, context_chunks: list[dict], stream: bool = True) -> str:
        messages = self._build_messages(query, context_chunks)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": 8192,
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }

        if not stream:
            resp = requests.post(self.api_url, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        resp = requests.post(self.api_url, json=payload, stream=True, timeout=120)
        resp.raise_for_status()

        full_text = []
        for line in resp.iter_lines():
            if line:
                import json
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    print(content, end="", flush=True)
                    full_text.append(content)
                if chunk.get("done"):
                    break

        print()
        return "".join(full_text)

    def check_health(self) -> bool:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
