from __future__ import annotations

import os
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv


SYSTEM_PROMPT = (
    "You are a BIS (Bureau of Indian Standards) compliance assistant for Indian MSEs. "
    "You will be given a product description query and retrieved BIS standards with scope summaries. "
    "Select the most relevant standard from the provided context and explain why in 2 concise sentences. "
    "Only mention IS standard numbers that appear in the provided context. Never invent standards."
)


class RationaleGenerator:
    def __init__(self) -> None:
        load_dotenv()
        self.provider = "fallback"
        self.model_name = "heuristic-rationale"
        self.status = "no-api-key"
        self.last_generation_mode = "fallback"
        self.last_error = ""
        self.llm = self._build_llm()

    def _build_llm(self):
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from langchain_groq import ChatGroq

                self.provider = "groq"
                self.model_name = "llama-3.3-70b-versatile"
                self.status = "ready"
                self.last_error = ""
                return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
            except Exception:
                self.provider = "fallback"
                self.model_name = "heuristic-rationale"
                self.status = "groq-import-failed"
                self.last_generation_mode = "fallback"
                self.last_error = "Failed to import langchain_groq or initialize ChatGroq."
                return None

        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self.provider = "google"
                self.model_name = "gemini-1.5-flash"
                self.status = "ready"
                self.last_error = ""
                return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
            except Exception:
                self.provider = "fallback"
                self.model_name = "heuristic-rationale"
                self.status = "google-import-failed"
                self.last_generation_mode = "fallback"
                self.last_error = "Failed to import langchain_google_genai or initialize Gemini client."
                return None

        return None

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
        try:
            response = self.llm.invoke(messages)
            self.last_generation_mode = "llm"
            self.last_error = ""
            return str(response.content).strip()
        except Exception as exc:
            self.status = "llm-call-failed"
            self.last_error = str(exc)
            return self.fallback_rationale(candidates)
