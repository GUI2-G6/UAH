from __future__ import annotations

import unittest

from app.services.gmail_scan import (
    ScanMessage,
    annotate_flat_scan_results_cluster_metadata,
    build_application_chain_key,
    build_thread_signature,
    evaluate_message,
    extract_canonical_employer_hint,
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

    def test_includes_non_ats_job_update_when_status_is_confident_in_hybrid_mode(self):
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
            source_strictness="hybrid_job_language",
        )
        self.assertTrue(evaluated["include"])
        self.assertTrue(evaluated["job_update_detected"])
        self.assertIsNone(evaluated["exclude_reason"])

    def test_includes_ats_message_when_no_applied_job_match(self):
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
        self.assertTrue(evaluated["include"])
        self.assertTrue(evaluated["ats_detected"])
        self.assertFalse(evaluated["matched_applied_job"])
        self.assertIsNone(evaluated["exclude_reason"])

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

    def test_body_status_wins_over_subject_and_snippet_signals(self):
        message = ScanMessage(
            subject="Interview invitation for Software Engineer",
            from_header="ATS <noreply@differentcorp.workday.com>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="Interview next steps available.",
            body=(
                "Thank you for your interest. We regret to inform you that we are "
                "unable to move forward with your application."
            ),
        )
        sessions = [{"id": 1, "company": "DifferentCorp", "job_title": "Software Engineer", "status": "submitted"}]
        evaluated = evaluate_message(
            message,
            apply_sessions=sessions,
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertEqual(evaluated["detected_status"], "rejection")

    def test_excludes_newsletter_promo_in_strict_mode(self):
        message = ScanMessage(
            subject="Your next deal awaits",
            from_header="Uber Eats <uber@uber.com>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="Don't miss these limited time offers.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
            linkedin_mode="linkedin_apply_only",
        )
        self.assertFalse(evaluated["include"])
        self.assertEqual(evaluated["exclude_reason"], "noncareer_source")

    def test_includes_linkedin_application_sent_email(self):
        message = ScanMessage(
            subject="Trent, your application was sent to Toyota Research Institute",
            from_header="LinkedIn <jobs-noreply@linkedin.com>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="Your application was sent to Toyota Research Institute",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
            linkedin_mode="linkedin_apply_only",
        )
        self.assertTrue(evaluated["include"])
        self.assertTrue(evaluated["linkedin_apply_detected"])

    def test_excludes_linkedin_premium_profile_email_in_apply_only_mode(self):
        message = ScanMessage(
            subject="Trent, enjoy this offer for LinkedIn Premium",
            from_header="LinkedIn <linkedin@em.linkedin.com>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="Premium members are more likely to get hired.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
            linkedin_mode="linkedin_apply_only",
        )
        self.assertFalse(evaluated["include"])
        self.assertEqual(evaluated["exclude_reason"], "linkedin_non_apply")

    def test_includes_candidatecare_additional_info_email(self):
        message = ScanMessage(
            subject="Additional Information Needed for the Position of 25-798",
            from_header="Granite Telecommunications Career Opportunities <do-not-reply@candidatecare.com>",
            date="Mon, 28 Apr 2026 10:00:00 -0400",
            snippet="Our recruiting team would like to review your application.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
            linkedin_mode="linkedin_apply_only",
        )
        self.assertTrue(evaluated["include"])
        self.assertEqual(evaluated["source_bucket"], "recruiter_direct")

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

    def test_includes_direct_company_offer_in_strict_mode_with_strong_language(self):
        message = ScanMessage(
            subject="Andover Companies: Summer Intern 2026",
            from_header="Tina Gioia <tgioia@andovercos.com>",
            date="Wed, 25 Feb 2026 14:49:00 -0500",
            snippet="We would love to have you join us as a Summer Intern in 2026.",
            body=(
                "Before I send the official offer letter, I wanted to make sure you are still interested. "
                "Reply to confirm your interest and we will prepare the formal offer letter."
            ),
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
        )
        self.assertTrue(evaluated["include"])
        self.assertEqual(evaluated["detected_status"], "offer")
        self.assertFalse(evaluated["ats_detected"])
        self.assertEqual(evaluated["source_bucket"], "recruiter_direct")

    def test_detects_offer_from_body_when_snippet_is_generic(self):
        message = ScanMessage(
            subject="Application update",
            from_header="Recruiting Team <recruiting@company.com>",
            date="Wed, 25 Feb 2026 14:49:00 -0500",
            snippet="Thanks for your patience while we review your candidacy.",
            body="We are pleased to extend a formal offer and will send your offer letter shortly.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
        )
        self.assertEqual(evaluated["detected_status"], "offer")
        self.assertTrue(evaluated["include"])

    def test_body_rejection_overrides_snippet_offer_signal(self):
        message = ScanMessage(
            subject="Status update",
            from_header="Recruiting Team <recruiting@company.com>",
            date="Wed, 25 Feb 2026 14:49:00 -0500",
            snippet="We are preparing your offer letter.",
            body="After careful review, we regret to inform you that we are not moving forward.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
        )
        self.assertEqual(evaluated["detected_status"], "rejection")
        self.assertTrue(evaluated["include"])

    def test_detects_pre_offer_interest_check_language(self):
        message = ScanMessage(
            subject="Quick check before formal offer",
            from_header="Hiring Team <hiring@acmecorp.com>",
            date="Wed, 25 Feb 2026 14:49:00 -0500",
            snippet="Before extending a formal offer, we wanted to confirm you are still interested.",
            body="Please reply by Friday so we can finalize your offer letter.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
        )
        self.assertEqual(evaluated["detected_status"], "offer")
        self.assertTrue(evaluated["include"])

    def test_detects_action_required_missing_info_language(self):
        message = ScanMessage(
            subject="Additional Information Needed for the Position of 25-798",
            from_header="Granite Telecommunications Career Opportunities <do-not-reply@candidatecare.com>",
            date="Tue, 3 Mar 2026 20:49:00 -0500",
            snippet=(
                "Some information appears to be missing from your Job Application. "
                "Please follow the below steps and complete our Job Application."
            ),
            body=(
                "Our recruiting team would like to review your application. "
                "Check your email inbox to retrieve the temporary password and "
                "proceed until you see a thank you message."
            ),
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
        )
        self.assertEqual(evaluated["detected_status"], "action_required")
        self.assertTrue(evaluated["include"])

    def test_excludes_newsletter_with_offer_language_boundary_case(self):
        message = ScanMessage(
            subject="Limited time offer from our newsletter",
            from_header="Marketing <news@updates.example.com>",
            date="Wed, 25 Feb 2026 14:49:00 -0500",
            snippet="View in browser and unsubscribe if you no longer wish to receive promos.",
            body="This limited time offer is for premium members only.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
            source_strictness="strict_career_domains",
        )
        self.assertFalse(evaluated["include"])
        self.assertEqual(evaluated["exclude_reason"], "noncareer_source")
        self.assertTrue(evaluated["negative_intent_detected"])

    def test_extracts_company_from_workday_localpart_when_subject_is_generic(self):
        message = ScanMessage(
            subject="Application status update",
            from_header="caci@myworkday.com",
            date="Sun, 23 Feb 2026 09:39:52 -0500",
            snippet="Thank you for your interest in this role.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertEqual(evaluated["company_hint"], "CACI")

    def test_extracts_company_from_position_at_subject_phrase(self):
        message = ScanMessage(
            subject="Thank you for your interest in the Software Development Intern position at CACI",
            from_header="caci@myworkday.com",
            date="Sun, 23 Feb 2026 09:39:52 -0500",
            snippet="After careful consideration, we are not moving forward.",
        )
        evaluated = evaluate_message(
            message,
            apply_sessions=[],
            allowed_statuses={"submitted"},
            require_ats=True,
        )
        self.assertEqual(evaluated["company_hint"], "CACI")

    def test_canonical_employer_pulls_hiring_company_from_ripplematch_forwarder(self):
        subject = "What's next with your application?"
        snippet = "Thanks for your interest in Expedia Group! Great news about your application."
        hint = extract_canonical_employer_hint(
            "Sara <sara@ripplematch.com>",
            subject,
            snippet,
            "",
            source_bucket="job_platform",
            company_hint="Ripplematch",
        )
        self.assertIsNotNone(hint)
        self.assertIn("expedia", hint.lower())

    def test_application_chain_key_unifies_expedia_vs_expedia_group_when_role_matches(self):
        shared_sub = "Candidate update — Software Engineering intern"
        shared_blob = (
            "Hello, for the position: Software Development Engineering Summer 2026 Intern — next steps attached."
        )
        sd1, sk1, ck1 = build_thread_signature(
            from_header="notifications <expedia@myworkday.com>",
            subject=shared_sub,
            company_hint="Expedia",
        )
        sd2, sk2, ck2 = build_thread_signature(
            from_header="Ripple <recruiter@ripplematch.com>",
            subject=shared_sub,
            company_hint="Ripplematch",
        )
        canon2 = extract_canonical_employer_hint(
            "Ripple <recruiter@ripplematch.com>",
            shared_sub,
            "Thanks for your interest in Expedia Group!",
            shared_blob,
            source_bucket="job_platform",
            company_hint="Ripplematch",
        )
        k1, ek1, rk1 = build_application_chain_key(
            canonical_company_hint=None,
            company_hint="Expedia Group",
            sender_domain=sd1,
            subject_key=sk1,
            company_key=ck1,
            subject=shared_sub,
            snippet_body=shared_blob,
        )
        k2, ek2, rk2 = build_application_chain_key(
            canonical_company_hint=canon2,
            company_hint="Ripplematch",
            sender_domain=sd2,
            subject_key=sk2,
            company_key=ck2,
            subject=shared_sub,
            snippet_body=shared_blob,
        )
        self.assertEqual(ek1, ek2)
        self.assertEqual(rk1, rk2)
        self.assertEqual(k1, k2)

    def test_cluster_annotation_assigns_ranks_and_leader(self):
        rows = [
            {
                "application_chain_key": "acme|intern",
                "thread_key": "",
                "date": "Mon, 02 Feb 2026 10:00:00 -0500",
                "source_id": "a-old",
            },
            {
                "application_chain_key": "acme|intern",
                "thread_key": "",
                "date": "Mon, 09 Feb 2026 10:00:00 -0500",
                "source_id": "b-new",
            },
        ]
        out = annotate_flat_scan_results_cluster_metadata(rows)
        sizes = {r["source_id"]: r["cluster_size"] for r in out}
        self.assertEqual(sizes["b-new"], 2)
        leaders = {r["source_id"]: r["cluster_leader_source_id"] for r in out}
        self.assertEqual(leaders["b-new"], "b-new")
        self.assertEqual(leaders["a-old"], "b-new")


if __name__ == "__main__":
    unittest.main()
