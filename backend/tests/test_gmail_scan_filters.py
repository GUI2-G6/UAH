from __future__ import annotations

import unittest

from app.services.gmail_scan import (
    ScanMessage,
    build_thread_signature,
    evaluate_message,
    normalize_company_key,
    normalize_subject_key,
)


class GmailScanFilterTests(unittest.TestCase):
    def test_thread_signature_is_stable_for_reply_forward_variants(self):
        sender_a, subject_a, company_a = build_thread_signature(
            from_header="Haier Workday <haier@myworkday.com>",
            subject="Re: Position Update from GE Appliances",
            company_hint="GE Appliances",
        )
        sender_b, subject_b, company_b = build_thread_signature(
            from_header="Haier Workday <haier@myworkday.com>",
            subject="Fwd: Position Update from GE Appliances",
            company_hint="Ge   Appliances",
        )
        self.assertEqual(sender_a, sender_b)
        self.assertEqual(subject_a, subject_b)
        self.assertEqual(company_a, company_b)

    def test_normalized_keys_strip_noise(self):
        self.assertEqual(normalize_subject_key("RE:   Position Update!!!"), "position update")
        self.assertEqual(normalize_company_key("GE Appliances, Inc."), "ge appliances inc")

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
        self.assertTrue(evaluated["ats_detected"])
        self.assertFalse(evaluated["matched_applied_job"])
        self.assertEqual(evaluated["exclude_reason"], "no_applied_job_match")

    def test_extracts_company_from_position_update_subject(self):
        message = ScanMessage(
            subject="Position Update from GE Appliances",
            from_header="Haier Workday <haier@myworkday.com>",
            date="Thu, 23 Apr 2026 03:54:24 -0400",
            snippet="Thanks for applying for our Software Engineering Co-op position.",
        )
        sessions = [{"id": 1, "company": "GE Appliances", "job_title": "Software Engineering Co-op", "status": "submitted"}]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertEqual(evaluated["company_hint"], "GE Appliances")
        self.assertTrue(evaluated["matched_applied_job"])

    def test_detects_workday_rejection_language(self):
        message = ScanMessage(
            subject="Position Update from GE Appliances",
            from_header="Haier Workday <haier@myworkday.com>",
            date="Thu, 23 Apr 2026 03:54:24 -0400",
            snippet=(
                "We've carefully reviewed your qualifications and regret to inform you "
                "that we are unable to consider you further for this position."
            ),
        )
        sessions = [{"id": 1, "company": "GE Appliances", "job_title": "Software Engineering Co-op", "status": "submitted"}]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertEqual(evaluated["detected_status"], "rejection")
        self.assertEqual(evaluated["company_hint"], "GE Appliances")

    def test_detects_rejection_from_body_when_snippet_is_generic(self):
        message = ScanMessage(
            subject="Position Update from GE Appliances",
            from_header="Haier Workday <haier@myworkday.com>",
            date="Thu, 23 Apr 2026 03:54:24 -0400",
            snippet="Status update on your application.",
            body=(
                "We've carefully reviewed your qualification and regret to inform you "
                "that we are unable to consider you further for this position."
            ),
        )
        sessions = [{"id": 1, "company": "GE Appliances", "job_title": "Software Engineering Co-op", "status": "submitted"}]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertEqual(evaluated["detected_status"], "rejection")

    def test_matches_company_acronym_with_title_overlap(self):
        message = ScanMessage(
            subject="Interview next steps for Software Engineering Co-op",
            from_header="Haier Workday <haier@myworkday.com>",
            date="Thu, 23 Apr 2026 03:54:24 -0400",
            snippet="The GE team would like to schedule your interview.",
        )
        sessions = [{"id": 1, "company": "General Electric", "job_title": "Software Engineering Co-op", "status": "submitted"}]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertTrue(evaluated["matched_applied_job"])


if __name__ == "__main__":
    unittest.main()
