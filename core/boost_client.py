from __future__ import annotations

import hmac
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests


@dataclass
class BoostClientConfig:
    base_url: str                      # e.g. https://company.boost.ai
    api_key: Optional[str] = None      # only if your deployment requires it
    use_signature: bool = False        # request hashing enabled?
    signing_secret: Optional[str] = None
    timeout_s: int = 30


@dataclass
class BoostConversation:
    conversation_id: str


class BoostChatClient:
    """
    Minimal wrapper for Boost.ai Chat API v2: POST /api/chat/v2
    - START conversation
    - POST text message (type=text, value="...")
    """
    def __init__(self, cfg: BoostClientConfig):
        self.cfg = cfg
        self.endpoint = cfg.base_url.rstrip("/") + "/api/chat/v2"

    def start(
        self,
        extra_start_payload: Optional[Dict[str, Any]] = None
    ) -> Tuple[BoostConversation, Dict[str, Any]]:
        payload: Dict[str, Any] = {"command": "START"}
        if extra_start_payload:
            payload.update(extra_start_payload)

        data = self._post(payload)

        conversation_id = self._extract_conversation_id(data)
        if not conversation_id:
            raise RuntimeError(f"START succeeded but conversation_id not found in response: {data}")

        return BoostConversation(conversation_id=conversation_id), data

    def post_text(self, conversation: BoostConversation, text: str) -> Dict[str, Any]:
        # Chat API v2 PostText expects: type="text" and value="<message>"
        payload: Dict[str, Any] = {
            "command": "POST",
            "conversation_id": conversation.conversation_id,
            "type": "text",
            "value": text,
        }
        return self._post(payload)

    # -----------------------
    # Internal helpers
    # -----------------------
    def _headers(self, raw_body: str) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # If your Boost deployment expects an API key/token, add it here.
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"

        # Optional request hashing / signature header (X-Hub-Signature)
        if self.cfg.use_signature:
            if not self.cfg.signing_secret:
                raise ValueError("use_signature=True but signing_secret is missing.")
            signature = hmac.new(
                self.cfg.signing_secret.encode("utf-8"),
                raw_body.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Hub-Signature"] = signature

        return headers

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw_body = json.dumps(payload, ensure_ascii=False)
        headers = self._headers(raw_body)

        try:
            resp = requests.post(
                self.endpoint,
                data=raw_body,
                headers=headers,
                timeout=self.cfg.timeout_s,
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Network error calling Boost Chat API: {e}") from e

        if resp.status_code >= 400:
            # 422 is “HTTPValidationError” in the docs  [oai_citation:1‡Chat API v2 _ boost.ai.pdf](file-service://file-XQXE1yExvXU6JgLPPHVuxk)
            raise RuntimeError(
                f"Boost Chat API error {resp.status_code} (url={resp.url}) body={resp.text!r}"
            )

        try:
            return resp.json()
        except ValueError:
            raise RuntimeError(f"Boost Chat API returned non-JSON response: {resp.text!r}")

    @staticmethod
    def _extract_conversation_id(data: Dict[str, Any]) -> Optional[str]:
        for key in ("conversation_id", "conversationId", "id"):
            if isinstance(data.get(key), str):
                return data[key]

        convo = data.get("conversation") or data.get("Conversation")
        if isinstance(convo, dict):
            for key in ("id", "conversation_id", "conversationId"):
                if isinstance(convo.get(key), str):
                    return convo[key]

        return None