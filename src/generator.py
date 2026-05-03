from __future__ import annotations

import os
import re
import time
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv


SYSTEM_PROMPT = (
    "You are a BIS (Bureau of Indian Standards) compliance assistant for Indian MSEs. "
    "You will be given a product description query and retrieved BIS standards with scope summaries. "
    "Select the most relevant standard from the provided context and explain why in 2 concise sentences. "
    "Only mention IS standard numbers that appear in the provided context. Never invent standards."
)
STANDARD_MENTION_RE = re.compile(r"IS\s+\d+(?:\s*\(Part\s*\d+\))?\s*:\s*\d{4}", re.IGNORECASE)


def normalize_std(std_string: str) -> str:
    return str(std_string).replace(" ", "").lower()


class RationaleGenerator:
    MAX_LLM_RETRIES = 3
    RETRY_BASE_DELAY_SECONDS = 0.2

    def __init__(self) -> None:
        load_dotenv()
        self.provider = "fallback"
        self.model_name = "heuristic-rationale"
        self.status = "no-api-key"
        self.last_generation_mode = "fallback"
        self.last_error = ""
        self.llm = None
        self.secondary_llm = None
        self.secondary_provider = ""
        self.secondary_model_name = ""
        self._build_llms()

    def _build_llms(self):
        groq_key = os.getenv("GROQ_API_KEY")
        groq_client = None
        if groq_key:
            try:
                from langchain_groq import ChatGroq

                groq_client = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
            except Exception:
                if not self.last_error:
                    self.last_error = "Failed to import langchain_groq or initialize ChatGroq."

        if groq_client is not None:
            self.llm = groq_client
            self.provider = "groq"
            self.model_name = "llama-3.3-70b-versatile"
            self.status = "ready"
            return

        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
                self.provider = "google"
                self.model_name = "gemini-1.5-flash"
                self.status = "ready"
                self.last_error = ""
                return
            except Exception:
                if not self.last_error:
                    self.last_error = "Failed to import langchain_google_genai or initialize Gemini client."

        self.provider = "fallback"
        self.model_name = "heuristic-rationale"
        if not self.last_error:
            self.last_error = "No valid LLM provider could be initialized."
        if groq_key and not groq_client:
            self.status = "groq-import-failed"
        elif google_key:
            self.status = "google-import-failed"
        else:
            self.status = "no-api-key"

    def available(self) -> bool:
        return self.llm is not None

    def info(self) -> Dict[str, str]:
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "llm_enabled": str(self.available()).lower(),
            "status": self.status,
            "last_generation_mode": self.last_generation_mode,
            "last_error": self.last_error,
        }

    def fallback_rationale(self, candidates: List[Dict[str, object]]) -> str:
        self.last_generation_mode = "fallback"
        top = candidates[0]["record"]
        return (
            f"{top['full_id']} is the strongest match because its title and scope align with the query. "
            f"The summary explicitly covers {top['scope'][:180].rstrip()}."
        )

    def validate_rationale(self, rationale: str, candidates: List[Dict[str, object]]) -> bool:
        allowed = {
            normalize_std(candidate["record"]["full_id"])
            for candidate in candidates[:5]
        }
        mentioned = {
            normalize_std(match.group(0))
            for match in STANDARD_MENTION_RE.finditer(rationale)
        }
        return mentioned.issubset(allowed)

    def generate(self, query: str, candidates: List[Dict[str, object]]) -> str:
        if not candidates:
            return "No matching BIS standard was retrieved from the indexed dataset."

        if self.llm is None:
            return self.fallback_rationale(candidates)

        context_lines = []
        for candidate in candidates[:5]:
            record = candidate["record"]
            context_lines.append(f"{record['full_id']} | {record['title']} | Scope: {record['scope']}")
        context = "\n".join(context_lines)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Query: {query}\n\nRetrieved standards:\n{context}\n\nWhich standard is most relevant and why?"),
        ]
        if self.try_llm(self.llm, self.provider, self.model_name, messages, candidates):
            return self.last_response

        if self.secondary_llm is not None:
            primary_error = self.last_error
            if self.try_llm(self.secondary_llm, self.secondary_provider, self.secondary_model_name, messages, candidates):
                self.status = "ready"
                self.last_error = ""
                return self.last_response
            self.last_error = f"Primary provider failed: {primary_error} | Secondary provider failed: {self.last_error}"

        self.status = "llm-call-failed"
        return self.fallback_rationale(candidates)

    def try_llm(self, llm, provider: str, model_name: str, messages, candidates: List[Dict[str, object]]) -> bool:
        last_exc: Exception | None = None
        for attempt in range(1, self.MAX_LLM_RETRIES + 1):
            try:
                response = llm.invoke(messages)
                content = str(response.content).strip()
                if not self.validate_rationale(content, candidates):
                    self.status = "hallucination-guard-fallback"
                    self.last_error = "LLM rationale mentioned a standard outside the retrieved candidate set."
                    return False
                self.provider = provider
                self.model_name = model_name
                self.status = "ready"
                self.last_generation_mode = "llm"
                self.last_error = ""
                self.last_response = content
                return True
            except Exception as exc:
                last_exc = exc
                if attempt < self.MAX_LLM_RETRIES:
                    time.sleep(self.RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))

        self.last_error = str(last_exc) if last_exc else "Unknown LLM call failure."
        return False
