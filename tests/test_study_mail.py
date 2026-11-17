import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import study_mail as mail


class MailTests(unittest.TestCase):
    def setUp(self):
        self.lessons = mail.load_lessons()
        self.state = {"week": 0, "week_monday": None, "deliveries": {}}

    def at(self, day):
        return datetime.fromisoformat(day + "T07:00:00").replace(tzinfo=mail.KST)

    def test_weekends_do_not_mutate_state(self):
        for day in ("2026-11-21", "2026-11-22"):
            self.assertIsNone(mail.reserve(self.state, self.at(day), self.lessons))
        self.assertEqual(self.state["deliveries"], {})

    def test_utc_sunday_is_korean_monday(self):
        now = datetime(2026, 11, 22, 22, tzinfo=timezone.utc).astimezone(mail.KST)
        self.assertEqual(mail.reserve(self.state, now, self.lessons)["id"], 1)

    def test_midweek_start_and_friday_review(self):
        self.assertEqual(mail.reserve(self.state, self.at("2026-11-18"), self.lessons)["id"], 3)
        self.assertEqual(mail.reserve(self.state, self.at("2026-11-20"), self.lessons)["id"], 5)
        self.assertEqual(mail.reserve(self.state, self.at("2026-11-23"), self.lessons)["id"], 6)

    def test_reservation_blocks_retries_even_before_sent(self):
        now = self.at("2026-11-16")
        mail.reserve(self.state, now, self.lessons)
        self.assertIsNone(mail.reserve(self.state, now, self.lessons))
        self.state["deliveries"]["2026-11-16"]["status"] = "sent"
        self.assertIsNone(mail.reserve(self.state, now, self.lessons))

    def test_four_week_cycle(self):
        for day, lesson_id in [("2026-11-16", 1), ("2026-11-23", 6),
                               ("2026-11-30", 11), ("2026-12-07", 16), ("2026-12-14", 1)]:
            self.assertEqual(mail.reserve(self.state, self.at(day), self.lessons)["id"], lesson_id)

    def test_html_escaped_and_three_sentences(self):
        lesson = copy.deepcopy(self.lessons[0])
        lesson["sentences"][0]["en"] = "<test> & hello"
        _, text, body = mail.render(lesson, "2026-11-16")
        self.assertIn("&lt;test&gt; &amp; hello", body)
        self.assertNotIn("<test>", body)
        self.assertEqual(body.count('<p style="margin:24px 0">'), 3)
        self.assertIn("3. ", text)

    def test_state_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            mail.reserve(self.state, self.at("2026-11-16"), self.lessons)
            mail.write_state(path, self.state)
            loaded = mail.read_state(path)
            self.assertIsNone(mail.reserve(loaded, self.at("2026-11-16"), self.lessons))

    def test_credentials_missing_and_header_injection(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Missing GitHub Secrets"):
                mail.credentials()
        with patch.dict("os.environ", {"GMAIL_ADDRESS": "a@example.com", "GMAIL_APP_PASSWORD": "test",
                                       "RECIPIENT_EMAIL": "b@example.com\nBcc: c@example.com"}, clear=True):
            with self.assertRaises(ValueError):
                mail.credentials()

    @patch("study_mail.smtplib.SMTP_SSL")
    def test_multipart_email_and_no_smtp_retry(self, smtp):
        config = {"GMAIL_ADDRESS": "sender@example.com", "GMAIL_APP_PASSWORD": "test",
                  "RECIPIENT_EMAIL": "recipient@example.com"}
        client = smtp.return_value.__enter__.return_value
        mail.send(self.lessons[0], "2026-11-16", config)
        msg = client.send_message.call_args.args[0]
        self.assertEqual(msg["To"], config["RECIPIENT_EMAIL"])
        self.assertEqual(msg.get_content_type(), "multipart/alternative")
        self.assertEqual(len(msg.get_payload()), 2)
        client.send_message.reset_mock()
        client.send_message.side_effect = TimeoutError
        with self.assertRaises(TimeoutError):
            mail.send(self.lessons[0], "2026-11-16", config)
        client.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
