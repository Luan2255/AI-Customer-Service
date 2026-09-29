import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.models import KnowledgeBaseEntry, Message

ALLOWED_INTENTS = {"duvida", "reclamacao", "suporte", "financeiro", "vendas", "cancelamento", "outros"}


@dataclass
class AssistantResult:
    """Normalized assistant output independent of the external provider response."""

    response: str
    intent: str
    human_required: bool = False
    escalation_reason: str | None = None


class LLMService:
    """Generate a structured reply using an API provider or the local development fallback."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(
        self,
        message: str,
        history: list[Message],
        knowledge: list[KnowledgeBaseEntry],
    ) -> AssistantResult:
        """Send conversation context to the configured model and normalize its result."""
        if not self.settings.llm_api_key:
            return self._fallback(message, knowledge)

        # The system instruction defines the response contract and escalation policy.
        system_prompt = (
            "Você é um assistente profissional de atendimento ao cliente. Responda em português, com clareza e empatia. "
            "Use o histórico e a base de conhecimento quando relevantes; não invente políticas. "
            "Retorne exclusivamente JSON com response (string), intent (uma de: dúvida, reclamação, suporte, "
            "financeiro, vendas, cancelamento, outros), human_required (boolean) e escalation_reason "
            "(string ou null). Escalone pedidos explícitos por humano, risco, ameaça, fraude ou casos sem solução segura."
        )
        # Include matched FAQ content before the recent conversation turns.
        context = "Base de conhecimento:\n" + "\n".join(
            f"P: {entry.question}\nR: {entry.answer}" for entry in knowledge
        )
        messages = [{"role": "system", "content": f"{system_prompt}\n\n{context}"}]
        messages.extend({"role": item.role, "content": item.content} for item in history)
        messages.append({"role": "user", "content": message})

        # Use the standard Chat Completions endpoint so compatible providers can be configured.
        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json={
                    "model": self.settings.llm_model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()

        # Convert provider JSON into a bounded, validated internal result.
        try:
            payload = json.loads(response.json()["choices"][0]["message"]["content"])
            intent = self._normalize_intent(payload.get("intent"))
            reason = payload.get("escalation_reason")
            return AssistantResult(
                response=str(payload["response"])[:10_000],
                intent=intent,
                human_required=bool(payload.get("human_required", False)),
                escalation_reason=str(reason)[:1_000] if reason else None,
            )
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise RuntimeError("O provedor LLM retornou uma resposta inválida.") from error

    @staticmethod
    def _normalize_intent(value: object) -> str:
        """Map supported intent labels to canonical names and unknown labels to 'outros'."""
        normalized = str(value or "outros").strip().lower()
        normalized = {"dúvida": "duvida", "reclamação": "reclamacao"}.get(normalized, normalized)
        return normalized if normalized in ALLOWED_INTENTS else "outros"

    @classmethod
    def _fallback(cls, message: str, knowledge: list[KnowledgeBaseEntry]) -> AssistantResult:
        """Provide a deterministic local reply when no external API key is configured."""
        normalized = message.casefold()

        # Use simple keyword patterns only for local development and automated tests.
        patterns = {
            "cancelamento": r"cancel|encerr|desist",
            "financeiro": r"cobran|fatura|pagamento|reembolso|preço|preco",
            "reclamacao": r"reclama|insatisfeit|absurdo|péssim|pessim",
            "suporte": r"erro|problema|não funciona|nao funciona|ajuda|suporte",
            "vendas": r"compr|contrat|plano|vender|preço|preco",
        }
        intent = next((name for name, pattern in patterns.items() if re.search(pattern, normalized)), "duvida")
        if re.search(r"humano|atendente|pessoa real", normalized):
            return AssistantResult(
                "Entendi. Vou encaminhar sua conversa para um atendente humano.",
                intent,
                True,
                "Solicitação explícita de atendimento humano.",
            )

        if knowledge:
            return AssistantResult(knowledge[0].answer, intent)
        return AssistantResult(
            "Entendi sua mensagem. Pode compartilhar mais detalhes para que eu possa ajudar?",
            intent,
        )