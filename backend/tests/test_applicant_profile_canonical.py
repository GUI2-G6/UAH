from types import SimpleNamespace
import unittest

from app.services.applicant_profile_canonical import (
    apply_profile_updates_to_canonical,
    derive_canonical_from_profile_fields,
    flatten_canonical_data,
    merge_review_into_profile,
    normalize_canonical_data,
    sync_profile_storage,
)


class ApplicantProfileCanonicalTests(unittest.TestCase):
    def test_sync_profile_storage_generates_canonical_and_token_map_from_flat_fields(self):
        profile = SimpleNamespace(
            first_name="Local",
            last_name="Developer",
            email="local@example.com",
            phone="",
            linkedin="https://linkedin.com/in/localdev",
            portfolio="https://local.dev",
            street_address="123 Main St",
            city="Huntsville",
            state="AL",
            zip="35801",
            summary="Frontend-focused builder.",
            degree="B.S.",
            major="Computer Science",
            university="UAH",
            grad_year="2025",
            gpa="3.8",
            years_experience="5",
            job_title="Frontend Engineer",
            skills_text="Vue, Python, SQL",
            certifications_text="AWS CCP",
            professional_links_text="GitHub: https://github.com/localdev",
            education_history_text="",
            employment_history_text="UAH | Frontend Engineer | Huntsville, AL | 2023 | Present",
            demographic_gender="",
            demographic_ethnicity="",
            veteran_status="",
            disability_status="",
            california_resident="",
            canonical_data=None,
            token_map=None,
        )

        canonical = sync_profile_storage(profile)

        self.assertEqual(canonical["personal_info"]["first_name"], "Local")
        self.assertEqual(canonical["education"][0]["institution"], "UAH")
        self.assertEqual(canonical["work_experience"][0]["title"], "Frontend Engineer")
        self.assertIn("personal_info.first_name", profile.token_map)
        self.assertIn("education[0].institution", profile.token_map)
        self.assertIn("work_experience[0].title", profile.token_map)
        self.assertEqual(profile.skills_text, "Vue, Python, SQL")

    def test_apply_profile_updates_to_canonical_preserves_existing_history(self):
        existing = normalize_canonical_data({
            "personal_info": {"first_name": "Local", "last_name": "Developer"},
            "education": [
                {"institution": "UAH", "degree": "B.S.", "field_of_study": "Computer Science", "end_date": "2025"},
                {"institution": "UAH", "degree": "M.S.", "field_of_study": "Software Engineering", "end_date": "2027"},
            ],
            "work_experience": [
                {"company": "UAH", "title": "Frontend Engineer"},
            ],
            "skills": {"technical": ["Vue"], "languages": [], "tools": [], "soft_skills": []},
        })

        updated = apply_profile_updates_to_canonical(existing, {
            "major": "Computer Engineering",
            "skills_text": "Vue, Python",
            "employment_history_text": "UAH | Frontend Engineer | Huntsville, AL | 2023 | Present\nOpenAI | Contract Engineer | Remote | 2026 | Present",
        })

        self.assertEqual(updated["education"][0]["field_of_study"], "Computer Engineering")
        self.assertEqual(updated["education"][1]["degree"], "M.S.")
        self.assertIn("Python", updated["skills"]["technical"])
        self.assertEqual(len(updated["work_experience"]), 3)
        self.assertEqual(updated["work_experience"][-1]["company"], "OpenAI")

    def test_merge_review_into_profile_defaults_to_existing_conflict_resolution(self):
        existing = derive_canonical_from_profile_fields({
            "first_name": "Local",
            "last_name": "Developer",
            "email": "old@example.com",
            "skills_text": "Vue",
            "job_title": "Frontend Engineer",
        })
        incoming = normalize_canonical_data({
            "personal_info": {"first_name": "Local", "last_name": "Developer", "email": "new@example.com"},
            "skills": {"technical": ["Vue", "Python"], "languages": [], "tools": [], "soft_skills": []},
            "work_experience": [{"company": "UAH", "title": "Staff Engineer"}],
        })

        merged_default, conflicts = merge_review_into_profile(existing, incoming, {})
        merged_override, _ = merge_review_into_profile(existing, incoming, {"personal_info.email": "incoming"})

        self.assertGreaterEqual(len(conflicts), 1)
        self.assertEqual(merged_default["personal_info"]["email"], "old@example.com")
        self.assertEqual(merged_override["personal_info"]["email"], "new@example.com")
        self.assertIn("skills.technical", flatten_canonical_data(merged_override))

    def test_sync_profile_storage_generates_derived_name_tokens_for_extension_contract(self):
        profile = SimpleNamespace(
            first_name="Taylor",
            middle_name="Alex",
            last_name="Example",
            suffix="Jr",
            full_legal_name="Taylor Alex Example Jr",
            preferred_name="Tay",
            email="taylor@example.com",
            phone="",
            linkedin="",
            portfolio="",
            street_address="",
            city="",
            state="",
            zip="",
            summary="",
            degree="",
            major="",
            university="",
            grad_year="",
            gpa="",
            years_experience="",
            job_title="",
            skills_text="",
            certifications_text="",
            professional_links_text="",
            education_history_text="",
            employment_history_text="",
            demographic_gender="",
            demographic_ethnicity="",
            veteran_status="",
            disability_status="",
            california_resident="",
            canonical_data=None,
            token_map=None,
        )

        sync_profile_storage(profile)

        self.assertEqual(profile.token_map["personal_info.middle_initial"], "A")
        self.assertEqual(profile.token_map["personal_info.first_middle_last"], "Taylor Alex Example")
        self.assertEqual(profile.token_map["personal_info.first_middle_last_with_suffix"], "Taylor Alex Example Jr")


if __name__ == "__main__":
    unittest.main()
