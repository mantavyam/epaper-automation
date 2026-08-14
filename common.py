#!/usr/bin/env python3
"""Shared helpers for the primary and fallback extraction scripts."""

import os
import json
import shutil
import logging
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

HISTORY_FILE = "download_history.json"
ARTIFACTS_DIR = "artifacts"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
STALE_ARTIFACT_DAYS = 4

# Paper name -> short code used in artifact filenames, e.g. TH-EDITORIAL-14-08-26.pdf
PAPER_CODES = {
    "The Hindu": "TH",
    "Indian Express": "IE",
}


def dated_filename(paper_name, doc_type, today, ext, part=None):
    """Build a filename like TH-EDITORIAL-14-08-26.pdf or TH-ART1-14-08-26.png.

    doc_type: e.g. "EDITORIAL", "ART", "FULL"
    part: appended directly after doc_type with no separator (ART + 1 -> "ART1")
    """
    code = PAPER_CODES.get(paper_name, paper_name.upper().replace(" ", ""))
    label = f"{doc_type}{part}" if part is not None else doc_type
    date_str = today.strftime("%d-%m-%y")
    return f"{code}-{label}-{date_str}.{ext}"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Invalid history file, starting fresh")
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def already_processed(history, date_key, month_key, paper_name):
    return (
        month_key in history
        and date_key in history[month_key]
        and paper_name in history[month_key][date_key]
    )


def record_history(history, date_key, month_key, paper_name, entry):
    history.setdefault(month_key, {}).setdefault(date_key, {})[paper_name] = entry
    save_history(history)


def artifact_dir_for(date_str):
    path = os.path.join(ARTIFACTS_DIR, date_str)
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_stale_artifacts(days=STALE_ARTIFACT_DAYS):
    if not os.path.isdir(ARTIFACTS_DIR):
        return
    cutoff = datetime.now().date() - timedelta(days=days)
    for name in os.listdir(ARTIFACTS_DIR):
        path = os.path.join(ARTIFACTS_DIR, name)
        if not os.path.isdir(path):
            continue
        try:
            folder_date = datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if folder_date < cutoff:
            shutil.rmtree(path)
            logger.info("Removed stale artifact folder: %s", path)


def post_discord(content, embed_title, embed_color, file_paths, date_str):
    """Post a message with one or more file attachments to the Discord webhook.

    file_paths: list of (filename, path) tuples.
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured")
        return False

    embed = {
        "title": embed_title,
        "color": embed_color,
        "timestamp": datetime.now().isoformat(),
        "footer": {"text": "E-Newspaper Editorial Extractor"},
    }
    payload = {"content": content, "embeds": [embed]}

    files = {}
    opened = []
    try:
        for idx, (filename, path) in enumerate(file_paths):
            fh = open(path, "rb")
            opened.append(fh)
            files[f"file{idx}"] = (filename, fh)

        response = requests.post(
            DISCORD_WEBHOOK_URL,
            data={"payload_json": json.dumps(payload)},
            files=files,
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Posted to Discord: %s", embed_title)
        return True
    except Exception as e:
        logger.error("Error posting to Discord: %s", e)
        return False
    finally:
        for fh in opened:
            fh.close()
