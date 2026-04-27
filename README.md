# 🚒 AI-Powered Runbook Assistant

A production-ready RAG (Retrieval-Augmented Generation) app that ingests your team's markdown runbooks and answers incident questions in plain English — via CLI or Slack bot.

📖 **Full Guide:** https://www.learnxops.com/project-ai-powered-runbook-assistant/

---

## Features

- **Working RAG pipeline** — markdown → header-aware chunking → embeddings → vector search → LLM answer
- **Multi-provider** — switch between Ollama (local), OpenAI, AWS Bedrock, and GCP Vertex AI via a single env var
- **ChromaDB vector store** — local persistent store with cosine similarity ANN index
- **Rich CLI** — `ingest`, `ask`, `interactive` REPL, and `stats` commands
- **Slack bot** — Socket Mode bot responds to @mentions and DMs
- **5 sample runbooks** — database outage, high CPU, deployment rollback, SSL expiry, on-call escalation
- **Source citations** — every answer includes which runbook(s) were used
# ai-powered-runbook-assistant
