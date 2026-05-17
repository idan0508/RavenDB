"""
Parse a Google Takeout .mbox file and export messages to JSON.

Output format: a JSON array of objects with Title, Body, Url, Date.

Usage:
  python scripts/collect_google_groups_mbox.py --mbox "C:\path\to\file.mbox"
"""

import argparse
import json
import mailbox
import os
import re
import sys
import uuid
from datetime import datetime
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser


class _HTMLToText(HTMLParser):
    """Minimal HTML to text converter for email bodies."""

    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        if data:
            self._chunks.append(data)

    def get_text(self):
        return " ".join(self._chunks)


def _strip_html(html):
    parser = _HTMLToText()
    parser.feed(html or "")
    return parser.get_text()


def _safe_get_text(part):
    try:
        return part.get_content()
    except Exception:
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except Exception:
            return payload.decode("utf-8", errors="replace")


def _extract_body(message):
    if message.is_multipart():
        text_parts = []
        html_parts = []
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                text_parts.append(_safe_get_text(part))
            elif content_type == "text/html":
                html_parts.append(_safe_get_text(part))
        if text_parts:
            return "\n".join(text_parts).strip()
        if html_parts:
            return _strip_html("\n".join(html_parts)).strip()
        return ""

    content_type = message.get_content_type()
    if content_type == "text/plain":
        return _safe_get_text(message).strip()
    if content_type == "text/html":
        return _strip_html(_safe_get_text(message)).strip()
    return ""


def _normalize_whitespace(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _message_to_record(message, index):
    subject = message.get("Subject", "")
    date_value = message.get("Date", "")
    message_id = message.get("Message-ID", "") or message.get("Message-Id", "")

    body = _extract_body(message)
    body = _normalize_whitespace(body)

    unique_id = ""
    if message_id:
        unique_id = message_id.strip().strip("<>")
    else:
        unique_id = str(uuid.uuid4())

    url = f"https://groups.google.com/g/ravendb/search?q={unique_id}"

    record = {
        "Title": subject.strip() or "No Subject",
        "Body": body,
        "Url": url,
        "Date": date_value,
    }
    return record


def parse_mbox_to_json(mbox_path, output_path):
    if not os.path.exists(mbox_path):
        raise FileNotFoundError(f"Mbox file not found: {mbox_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    mbox = mailbox.mbox(mbox_path, factory=None)

    total = 0
    written = 0

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("[\n")
        first = True

        for key in mbox.iterkeys():
            try:
                raw = mbox.get_bytes(key)
                message = BytesParser(policy=policy.default).parsebytes(raw)
            except Exception:
                total += 1
                continue

            record = _message_to_record(message, total)
            total += 1

            if not record["Body"]:
                continue

            if not first:
                out.write(",\n")
            out.write(json.dumps(record, ensure_ascii=True))
            first = False
            written += 1

            if written % 1000 == 0:
                print(f"Processed {total} messages, wrote {written}")

        out.write("\n]\n")

    print(f"Done. Total messages: {total}, written: {written}")
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Parse Google Groups mbox to JSON")
    parser.add_argument("--mbox", required=True, help="Path to the .mbox file")
    parser.add_argument(
        "--output",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "collected_discussions",
            "google_groups_latest.json",
        ),
        help="Output JSON file path",
    )
    args = parser.parse_args()

    parse_mbox_to_json(args.mbox, args.output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(1)
