#!/usr/bin/env python3
"""
Slack Bot interface for the AI Runbook Assistant.

Setup:
  1. Create a Slack App at https://api.slack.com/apps
  2. Enable Socket Mode and add app-level token (xapp-...)
  3. Add OAuth scopes: app_mentions:read, chat:write, im:history, im:read
  4. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env
  5. Run: python slack_bot.py

Usage:
  - @mention the bot in any channel: @RunbookBot our DB is down, what do I do?
  - DM the bot directly with any incident question
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = App(token=os.environ["SLACK_BOT_TOKEN"])

PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


def _build_slack_blocks(answer: str, sources: list[str], question: str) -> list[dict]:
    """Build Slack Block Kit response."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🤖 Runbook Assistant", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Question:* {question}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": answer},
        },
    ]

    if sources:
        source_list = " • ".join(f"`{s}`" for s in sources)
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📚 *Sources:* {source_list}",
                    }
                ],
            }
        )

    return blocks


def _answer_question(question: str, say, logger_ref) -> None:
    """Core answer logic shared by mention and DM handlers."""
    try:
        from src.query import ask as rag_ask

        say(text="🔍 Searching runbooks...", blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "🔍 Searching runbooks, one moment..."},
            }
        ])

        result = rag_ask(question, PERSIST_DIR)
        blocks = _build_slack_blocks(result.answer, result.sources, question)
        say(text=result.answer, blocks=blocks)

    except Exception as e:
        logger_ref.error(f"Error answering: {e}", exc_info=True)
        say(
            text=f"❌ Sorry, I hit an error: `{e}`\n"
            "Please ensure runbooks are ingested (`python cli.py ingest`)."
        )


@app.event("app_mention")
def handle_mention(event, say, logger):
    """Respond to @mentions in channels."""
    raw_text: str = event.get("text", "")
    parts = raw_text.split(maxsplit=1)
    question = parts[1].strip() if len(parts) > 1 else ""

    if not question:
        say(
            "Hi! I'm your Runbook Assistant 🚒\n"
            "Ask me any incident question and I'll search your team's runbooks.\n"
            "_Example: @RunbookBot our database is throwing too many connections_"
        )
        return

    _answer_question(question, say, logger)


@app.event("message")
def handle_dm(event, say, logger):
    """Respond to direct messages (DMs)."""
    if event.get("channel_type") != "im":
        return

    question = event.get("text", "").strip()
    if not question or event.get("subtype"):
        return

    _answer_question(question, say, logger)


if __name__ == "__main__":
    logger.info("Starting AI Runbook Assistant Slack bot...")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
