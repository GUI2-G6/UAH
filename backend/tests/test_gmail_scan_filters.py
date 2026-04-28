from __future__ import annotations

import unittest

from app.services.gmail_scan import ScanMessage, evaluate_message


class GmailScanFilterTests(unittest.TestCase):
    def test_includes_ats_message_that_matches_submitted_apply_session(self):
        message = ScanMessage(
            subject="Interview next steps at Acme Robotics",
            from_header="Acme Recruiting <noreply@acme.greenhouse.io>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="We would like to schedule your interview for Software Engineer.",
        )
        sessions = [
            {"id": 1, "company": "Acme Robotics", "job_title": "Software Engineer", "status": "submitted"}
        ]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertTrue(evaluated["include"])
        self.assertEqual(evaluated["detected_status"], "interview_invite")
        self.assertTrue(evaluated["ats_detected"])
        self.assertTrue(evaluated["matched_applied_job"])

    def test_excludes_non_ats_message_even_if_keyword_match(self):
        message = ScanMessage(
            subject="Interview next steps",
            from_header="Friend <friend@gmail.com>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="Congrats, interview invite happened.",
        )
        sessions = [{"id": 1, "company": "Acme Robotics", "job_title": "Software Engineer", "status": "submitted"}]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertFalse(evaluated["include"])
        self.assertEqual(evaluated["exclude_reason"], "non_ats_sender")

    def test_excludes_ats_message_when_no_applied_job_match(self):
        message = ScanMessage(
            subject="Application received at DifferentCorp",
            from_header="ATS <noreply@differentcorp.workday.com>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="Thank you for applying.",
        )
        sessions = [{"id": 1, "company": "Acme Robotics", "job_title": "Software Engineer", "status": "submitted"}]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertFalse(evaluated["include"])
        self.assertEqual(evaluated["exclude_reason"], "no_applied_job_match")


if __name__ == "__main__":
    unittest.main()
