"""Device AI injection gateway.

This example shows a *safe* way to "inject AI" into your own apps by running
an HTTP gateway on each device and letting approved applications call it.

It does NOT access ChatGPT account sessions or other apps without consent.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel


@dataclass
class InjectionPolicy:
    """Allow-list policy for app-level AI integration."""

    allowed_apps: set[str]

    def can_inject(self, app_name: str) -> bool:
        return app_name in self.allowed_apps


class DeviceAIInjector:
    """Owns a single AI agent and processes injection requests."""

    def __init__(self, policy: InjectionPolicy) -> None:
        self.policy = policy
        self.agent = ReActAgent(
            name="DeviceAIAgent",
            sys_prompt=(
                "You are an assistant embedded into approved local apps. "
                "Return concise, practical suggestions in JSON-like bullet form. "
                "Never claim access to external accounts or hidden device data."
            ),
            model=OpenAIChatModel(
                model_name=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                api_key=require_env_var("OPENAI_API_KEY"),
                stream=False,
            ),
            memory=InMemoryMemory(),
            formatter=DashScopeChatFormatter(),
        )

    async def inject(self, payload: dict[str, Any]) -> dict[str, Any]:
        app_name = str(payload.get("app_name", ""))
        if not self.policy.can_inject(app_name):
            return {
                "ok": False,
                "error": f"App '{app_name}' is not in ALLOWED_APPS.",
            }

        prompt = (
            f"Device: {payload.get('device_id', 'unknown')}\n"
            f"App: {app_name}\n"
            f"Task: {payload.get('task', 'No task provided')}\n"
            f"Context: {json.dumps(payload.get('context', {}), ensure_ascii=False)}"
        )

        response = await self.agent(prompt)
        return {
            "ok": True,
            "device_id": payload.get("device_id"),
            "app_name": app_name,
            "ai_response": response.get_text_content(),
        }


def require_env_var(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable '{name}' must be set.")
    return value


def build_injector() -> DeviceAIInjector:
    raw = os.getenv("ALLOWED_APPS", "notes,calendar,mail")
    policy = InjectionPolicy(allowed_apps={item.strip() for item in raw.split(",")})
    return DeviceAIInjector(policy=policy)


INJECTOR = build_injector()


class InjectionHandler(BaseHTTPRequestHandler):
    """HTTP API: POST /inject"""

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/inject":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))

            result = asyncio.run(INJECTOR.inject(payload))
            status = HTTPStatus.OK if result.get("ok") else HTTPStatus.FORBIDDEN
            self._send_json(status, result)
        except json.JSONDecodeError:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Invalid JSON payload."},
            )
        except Exception as exc:  # pragma: no cover - example error path
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": f"Server error: {exc}"},
            )


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), InjectionHandler)
    print(f"Device AI Injection Gateway listening on http://{host}:{port}")
    print("POST /inject with JSON: device_id, app_name, task, context")
    server.serve_forever()


if __name__ == "__main__":
    main()
