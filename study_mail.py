"""Weekday conversation email. Python 3.11+, standard library only."""
import argparse
import html
import json
import os
from pathlib import Path
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
KST = ZoneInfo("Asia/Seoul")


def load_lessons():
    lessons = json.loads((ROOT / "curriculum/lessons.json").read_text(encoding="utf-8"))
    if not lessons or len(lessons) % 5:
        raise ValueError("Curriculum must contain complete five-day weeks")
    for i, lesson in enumerate(lessons):
        if lesson["id"] != i + 1 or len(lesson["sentences"]) != 3:
            raise ValueError("Each lesson needs a sequential ID and exactly three sentences")
        if not lesson["topic"] or not lesson["note"]:
            raise ValueError("Missing topic or note")
        for sentence in lesson["sentences"]:
            if not sentence["en"].strip() or not sentence["ko"].strip():
                raise ValueError("Missing sentence or translation")
    return lessons


def render(lesson, day):
    subject = f"[아침영어 {lesson['id']:02d}] {lesson['topic']}"
    lines = [subject, day, ""]
    cards = []
    for i, s in enumerate(lesson["sentences"], 1):
        lines += [f"{i}. {s['en']}", s["ko"], ""]
        cards.append(f'<p style="margin:24px 0"><strong>{i}. {html.escape(s["en"])}</strong>'
                     f'<br><span style="color:#586174">{html.escape(s["ko"])}</span></p>')
    lines += ["오늘의 포인트", lesson["note"]]
    body = (f'<!doctype html><html lang="ko"><meta charset="utf-8"><body '
            f'style="margin:0;background:#f4f6fa;font-family:Arial,sans-serif">'
            f'<div style="max-width:580px;margin:24px auto;padding:28px;background:white;'
            f'line-height:1.7;color:#17243b"><small>DAILY STUDY · {html.escape(day)}</small>'
            f'<h2 style="font-size:21px">{html.escape(lesson["topic"])}</h2>'
            + "".join(cards) + '<hr style="border:0;border-top:1px solid #e2e7ef">'
            f'<p><strong>오늘의 포인트</strong><br>{html.escape(lesson["note"])}</p></div></body></html>')
    return subject, "\n".join(lines), body


def credentials():
    names = ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "RECIPIENT_EMAIL")
    values = {name: os.environ.get(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError("Missing GitHub Secrets: " + ", ".join(missing))
    for name in ("GMAIL_ADDRESS", "RECIPIENT_EMAIL"):
        value = values[name]
        if "@" not in value or any(c in value for c in "\r\n,; "):
            raise ValueError(f"Invalid single email address in {name}")
    values["GMAIL_APP_PASSWORD"] = values["GMAIL_APP_PASSWORD"].replace(" ", "")
    return values


def read_state(path):
    if not path.exists():
        return {"week": 0, "week_monday": None, "deliveries": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def reserve(state, now, lessons):
    """Persist this reservation BEFORE SMTP. Never automatically retry uncertain sends."""
    from datetime import timedelta
    if now.weekday() >= 5:
        return None
    day = now.date().isoformat()
    if day in state["deliveries"]:
        return None
    monday = (now.date() - timedelta(days=now.weekday())).isoformat()
    if state["week_monday"] != monday:
        if state["week_monday"] is not None:
            state["week"] += 1
        state["week_monday"] = monday
    index = (state["week"] % (len(lessons) // 5)) * 5 + now.weekday()
    state["deliveries"][day] = {"lesson_id": lessons[index]["id"], "status": "reserved"}
    return lessons[index]


def send(lesson, day, config):
    subject, text, body = render(lesson, day)
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["GMAIL_ADDRESS"]
    message["To"] = config["RECIPIENT_EMAIL"]
    message["Date"] = format_datetime(datetime.now(KST))
    message["Message-ID"] = f"<dailystudy-{day}@{config['GMAIL_ADDRESS'].split('@')[1]}>"
    message.set_content(text)
    message.add_alternative(body, subtype="html")
    # A connection failure after DATA may still mean Gmail accepted the email.
    # Do not retry SMTP automatically; the persisted reservation prevents duplicates.
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(config["GMAIL_ADDRESS"], config["GMAIL_APP_PASSWORD"])
        smtp.send_message(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preview", "validate", "reserve", "send"), nargs="?", default="preview")
    parser.add_argument("--lesson", type=int, default=1)
    parser.add_argument("--state", type=Path, default=ROOT / "mail_state/state.json")
    args = parser.parse_args()
    lessons = load_lessons()
    now = datetime.now(KST)
    day = now.date().isoformat()
    if args.command == "validate":
        print(f"Validated {len(lessons)} lessons / {len(lessons) * 3} sentences.")
        return
    if args.command == "preview":
        if not 1 <= args.lesson <= len(lessons):
            parser.error("Lesson number out of range")
        _, text, body = render(lessons[args.lesson - 1], day)
        output = ROOT / "preview"
        output.mkdir(exist_ok=True)
        (output / "email.html").write_text(body, encoding="utf-8")
        (output / "email.txt").write_text(text, encoding="utf-8")
        print(text)
        print("\nPreview: preview/email.html (no email sent)")
        return
    # Weekend policy also applies to manual workflow runs.
    if now.weekday() >= 5:
        print("Weekend: no email sent.")
        return
    config = credentials()
    state = read_state(args.state)
    if args.command == "reserve":
        lesson = reserve(state, now, lessons)
        if lesson is None:
            print("Already reserved or sent today: skipped.")
            return
        write_state(args.state, state)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"ready=true\nday={day}\n")
        print(f"Reserved lesson {lesson['id']} for {day}.")
        return
    delivery = state["deliveries"].get(day)
    if not delivery or delivery["status"] != "reserved":
        raise ValueError("A persisted reservation for today is required")
    if os.environ.get("RESERVED_DAY") != day:
        raise ValueError("Missing or stale reservation; run the workflow reserve step first")
    lesson = next(item for item in lessons if item["id"] == delivery["lesson_id"])
    send(lesson, day, config)
    delivery["status"] = "sent"
    write_state(args.state, state)
    print(f"Gmail accepted lesson {lesson['id']} for delivery.")


if __name__ == "__main__":
    try:
        main()
    except (smtplib.SMTPException, OSError) as exc:
        # SMTP exceptions can contain private recipient details. Log only the class.
        raise SystemExit(f"Mail operation failed ({type(exc).__name__}). Check account settings; reservation is kept.") from None
