from __future__ import annotations

"""
Provider abstraction for LLM chat and embedding calls.

Supported providers (set via LLM_PROVIDER env var):
  openai   — OpenAI API (default)
  bedrock  — AWS Bedrock (Claude 3.5 Sonnet + Titan Embeddings V2)
  vertex   — GCP Vertex AI (Gemini 1.5 Pro + text-embedding-004)
  ollama   — Ollama local inference (Llama 3, Mistral, etc.)

AWS Bedrock auth: boto3 credential chain (env vars / ~/.aws/credentials / IAM role)
GCP Vertex auth:  Application Default Credentials (gcloud auth / service account key /
                  Workload Identity)
Ollama:           Runs locally; set OLLAMA_BASE_URL if not on http://localhost:11434
"""

import json
import os
from typing import List


# ---------------------------------------------------------------------------
# Bedrock shared helper
# ---------------------------------------------------------------------------

def _bedrock_client():
    """
    Build a boto3 bedrock-runtime client.

    Credential priority:
      1. Explicit Bedrock-scoped keys:  BEDROCK_ACCESS_KEY_ID + BEDROCK_SECRET_ACCESS_KEY
         (optionally BEDROCK_SESSION_TOKEN for temporary/STS credentials)
      2. Standard boto3 credential chain: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY,
         ~/.aws/credentials, IAM instance role, etc.

    Region: BEDROCK_REGION > AWS_REGION > AWS_DEFAULT_REGION > us-east-1
    """
    import boto3

    region = os.getenv(
        "BEDROCK_REGION",
        os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
    )

    access_key = os.getenv("BEDROCK_ACCESS_KEY_ID")
    secret_key = os.getenv("BEDROCK_SECRET_ACCESS_KEY")
    session_token = os.getenv("BEDROCK_SESSION_TOKEN")  # optional

    kwargs: dict = {"region_name": region}
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key
        if session_token:
            kwargs["aws_session_token"] = session_token

    return boto3.client("bedrock-runtime", **kwargs)


# ---------------------------------------------------------------------------
# Embedding providers
# ---------------------------------------------------------------------------

class OpenAIEmbedder:
    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self._model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]


class BedrockEmbedder:
    """
    Uses Amazon Titan Embeddings V2 via AWS Bedrock.
    Model: amazon.titan-embed-text-v2:0  (1024-dim)
    Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html
    """

    DEFAULT_MODEL = "amazon.titan-embed-text-v2:0"

    def __init__(self) -> None:
        self._client = _bedrock_client()
        self._model = os.getenv("BEDROCK_EMBEDDING_MODEL", self.DEFAULT_MODEL)

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            body = json.dumps({"inputText": text})
            response = self._client.invoke_model(
                modelId=self._model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            vectors.append(result["embedding"])
        return vectors

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]


# ---------------------------------------------------------------------------
# LLM chat providers
# ---------------------------------------------------------------------------

class OpenAIChat:
    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self._model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")

    def complete(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()


class BedrockChat:
    """
    Uses Claude 3 on AWS Bedrock via the Converse API.
    Default model: anthropic.claude-3-5-sonnet-20241022-v2:0
    Other options:
      anthropic.claude-3-haiku-20240307-v1:0   (fast, cheap)
      anthropic.claude-3-opus-20240229-v1:0    (most capable)
    Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
    """

    DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    def __init__(self) -> None:
        self._client = _bedrock_client()
        self._model = os.getenv("BEDROCK_CHAT_MODEL", self.DEFAULT_MODEL)

    def complete(self, system_prompt: str, user_message: str) -> str:
        response = self._client.converse(
            modelId=self._model,
            system=[{"text": system_prompt}],
            messages=[
                {"role": "user", "content": [{"text": user_message}]}
            ],
            inferenceConfig={"temperature": 0.2},
        )
        return response["output"]["message"]["content"][0]["text"].strip()


# ---------------------------------------------------------------------------
# Ollama (local) providers
# ---------------------------------------------------------------------------

class OllamaEmbedder:
    """
    Uses Ollama's local embedding endpoint.
    Default model: nomic-embed-text (768-dim).
    Other options: mxbai-embed-large, all-minilm, etc.
    Docs: https://github.com/ollama/ollama-python
    """

    DEFAULT_MODEL = "nomic-embed-text"

    def __init__(self) -> None:
        import ollama

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._client = ollama.Client(host=base_url)
        self._model = os.getenv("OLLAMA_EMBEDDING_MODEL", self.DEFAULT_MODEL)

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [
            self._client.embeddings(model=self._model, prompt=text)["embedding"]
            for text in texts
        ]

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]


class OllamaChat:
    """
    Uses Ollama's local chat endpoint.
    Default model: llama3.2
    Other options: llama3.1, mistral, gemma3, phi4, etc.
    Docs: https://github.com/ollama/ollama-python
    """

    DEFAULT_MODEL = "llama3.2"

    def __init__(self) -> None:
        import ollama

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._client = ollama.Client(host=base_url)
        self._model = os.getenv("OLLAMA_CHAT_MODEL", self.DEFAULT_MODEL)

    def complete(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.2},
        )
        return response["message"]["content"].strip()


# ---------------------------------------------------------------------------
# GCP Vertex AI providers
# ---------------------------------------------------------------------------

class VertexAIEmbedder:
    """
    Uses Vertex AI text-embedding-004 (768-dim).
    Auth: Application Default Credentials (ADC).
      - Local: run `gcloud auth application-default login`
      - GCE/Cloud Run/GKE: attach a service account with roles/aiplatform.user
      - CI/key file: set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
    Docs: https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings
    """

    DEFAULT_MODEL = "text-embedding-004"

    def __init__(self) -> None:
        import vertexai
        from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

        project = os.environ["VERTEX_PROJECT"]
        location = os.getenv("VERTEX_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)
        model_name = os.getenv("VERTEX_EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self._model = TextEmbeddingModel.from_pretrained(model_name)
        self._TextEmbeddingInput = TextEmbeddingInput

    def embed(self, texts: List[str]) -> List[List[float]]:
        inputs = [self._TextEmbeddingInput(text, task_type="RETRIEVAL_DOCUMENT") for text in texts]
        embeddings = self._model.get_embeddings(inputs)
        return [e.values for e in embeddings]

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]


class VertexAIChat:
    """
    Uses Gemini on Vertex AI via the GenerativeModel API.
    Default model: gemini-1.5-pro-002
    Other options:
      gemini-1.5-flash-002   (fast, low cost)
      gemini-2.0-flash-001   (latest flash)
    Docs: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-chat-prompts-gemini
    """

    DEFAULT_MODEL = "gemini-1.5-pro-002"

    def __init__(self) -> None:
        import vertexai
        from vertexai.generative_models import GenerationConfig, GenerativeModel

        project = os.environ["VERTEX_PROJECT"]
        location = os.getenv("VERTEX_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)
        model_name = os.getenv("VERTEX_CHAT_MODEL", self.DEFAULT_MODEL)
        self._model = GenerativeModel(model_name)
        self._gen_config = GenerationConfig(temperature=0.2)

    def complete(self, system_prompt: str, user_message: str) -> str:
        from vertexai.generative_models import Content, Part

        full_prompt = f"{system_prompt}\n\n{user_message}"
        response = self._model.generate_content(
            full_prompt,
            generation_config=self._gen_config,
        )
        return response.text.strip()


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def get_embedder() -> OpenAIEmbedder | BedrockEmbedder | VertexAIEmbedder | OllamaEmbedder:
    """Return the configured embedding client based on LLM_PROVIDER."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "bedrock":
        return BedrockEmbedder()
    if provider == "vertex":
        return VertexAIEmbedder()
    if provider == "ollama":
        return OllamaEmbedder()
    return OpenAIEmbedder()


def get_chat() -> OpenAIChat | BedrockChat | VertexAIChat | OllamaChat:
    """Return the configured chat client based on LLM_PROVIDER."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "bedrock":
        return BedrockChat()
    if provider == "vertex":
        return VertexAIChat()
    if provider == "ollama":
        return OllamaChat()
    return OpenAIChat()
