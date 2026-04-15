from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from fastapi import UploadFile

from app.api import resume as resume_api
from app.services import resume_parser


class _FakeUploadQuery:
    def __init__(self, db, call_index):
        self._db = db
        self._call_index = call_index

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def scalar(self):
        if self._call_index != 1:
            raise AssertionError("Unexpected scalar() call")
        return self._db.resume_count

    def first(self):
        if self._call_index != 2:
            raise AssertionError("Unexpected first() call")
        return self._db.last_upload


class _FakeUploadDb:
    def __init__(self, resume_count=0, last_upload=None):
        self.resume_count = resume_count
        self.last_upload = last_upload
        self.query_calls = 0
        self.added = None
        self.commits = 0

    def query(self, *args, **kwargs):
        self.query_calls += 1
        return _FakeUploadQuery(self, self.query_calls)

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 101


class _FakeQueueQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)


class _FakeQueueDb:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _FakeQueueQuery(self._rows)


class _FakeResumeByIdQuery:
    def __init__(self, resume):
        self._resume = resume

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._resume


class _FakeResumeByIdDb:
    def __init__(self, resume):
        self._resume = resume
        self.commits = 0

    def query(self, _model):
        return _FakeResumeByIdQuery(self._resume)

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        return None


class ResumePipelineContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_stores_pdf_without_running_ocr(self):
        fake_db = _FakeUploadDb()
        current_user = SimpleNamespace(id=7)
        upload = UploadFile(filename="resume.pdf", file=BytesIO(b"%PDF-1.4 mock"))

        with patch.object(resume_api.settings, "USE_LOCAL_PIPELINE", True), \
             patch.object(
                 resume_parser,
                 "ocr_pdf",
                 AsyncMock(side_effect=AssertionError("Cloud OCR should not run during upload")),
             ), \
             patch.object(
                 resume_parser,
                 "ocr_pdf_local",
                 AsyncMock(side_effect=AssertionError("Local OCR should not run during upload")),
             ):
            response = await resume_api.upload_resume(
                file=upload,
                db=fake_db,
                current_user=current_user,
            )

        self.assertEqual(response.id, 101)
        self.assertEqual(response.file_name, "resume.pdf")
        self.assertEqual(response.status, "uploaded")
        self.assertIsNotNone(fake_db.added)
        self.assertEqual(fake_db.added.user_id, 7)
        self.assertEqual(fake_db.added.file_name, "resume.pdf")
        self.assertEqual(fake_db.added.pdf_data, b"%PDF-1.4 mock")
        self.assertIsNone(fake_db.added.raw_markdown)
        self.assertEqual(fake_db.commits, 1)

    async def test_cloud_parse_input_uses_cloud_ocr_even_when_local_pipeline_flag_enabled(self):
        cloud_ocr = AsyncMock(return_value={"ok": True, "md_results": "cloud text"})
        local_ocr = AsyncMock(return_value={"ok": True, "md_results": "local text"})

        with patch.object(resume_parser.settings, "USE_LOCAL_PIPELINE", True), \
             patch.object(resume_parser, "ocr_pdf", cloud_ocr), \
             patch.object(resume_parser, "ocr_pdf_local", local_ocr):
            payload = await resume_parser.get_parse_input_text(b"pdf-bytes", "cloud")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["text"], "cloud text")
        self.assertEqual(payload["source"], "cloud_ocr")
        cloud_ocr.assert_awaited_once_with(b"pdf-bytes")
        local_ocr.assert_not_awaited()

    async def test_cloud_parse_input_reuses_cached_cloud_ocr_markdown(self):
        resume = SimpleNamespace(
            raw_markdown="cached cloud text",
            raw_markdown_method="cloud",
            raw_markdown_source="cloud_ocr",
        )
        cloud_ocr = AsyncMock(return_value={"ok": True, "md_results": "fresh cloud text"})

        with patch.object(resume_parser, "ocr_pdf", cloud_ocr):
            payload = await resume_parser.get_parse_input_text(
                b"pdf-bytes",
                "cloud",
                resume=resume,
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["text"], "cached cloud text")
        self.assertEqual(payload["source"], "cloud_ocr")
        self.assertEqual(payload["cache_hit"], True)
        cloud_ocr.assert_not_awaited()

    async def test_rules_parse_input_uses_embedded_text_only(self):
        extract_text = Mock(return_value={"ok": True, "text": "embedded text", "source": "rules_embedded_pdf_text"})
        cloud_ocr = AsyncMock(return_value={"ok": True, "md_results": "cloud text"})
        local_ocr = AsyncMock(return_value={"ok": True, "md_results": "local text"})

        with patch.object(resume_parser.settings, "USE_LOCAL_PIPELINE", True), \
             patch.object(resume_parser, "extract_embedded_pdf_text", extract_text), \
             patch.object(resume_parser, "ocr_pdf", cloud_ocr), \
             patch.object(resume_parser, "ocr_pdf_local", local_ocr):
            payload = await resume_parser.get_parse_input_text(b"pdf-bytes", "rules")

        self.assertEqual(payload["text"], "embedded text")
        self.assertEqual(payload["source"], "rules_embedded_pdf_text")
        extract_text.assert_called_once_with(b"pdf-bytes")
        cloud_ocr.assert_not_awaited()
        local_ocr.assert_not_awaited()

    async def test_cloud_markdown_parse_uses_cloud_llm_even_when_local_pipeline_flag_enabled(self):
        cloud_llm = AsyncMock(return_value={"parsed": "cloud"})
        local_llm = AsyncMock(return_value={"parsed": "local"})

        with patch.object(resume_parser.settings, "USE_LOCAL_PIPELINE", True), \
             patch.object(resume_parser, "categorize_with_llm", cloud_llm), \
             patch.object(resume_parser, "categorize_with_local_llm", local_llm):
            structured = await resume_parser.parse_markdown_by_method("resume markdown", "cloud")

        self.assertEqual(structured, {"parsed": "cloud"})
        cloud_llm.assert_awaited_once_with("resume markdown")
        local_llm.assert_not_awaited()

    async def test_rules_markdown_parse_uses_rules_parser_only(self):
        rules_parser = Mock(return_value={"parsed": "rules"})
        cloud_llm = AsyncMock(return_value={"parsed": "cloud"})
        local_llm = AsyncMock(return_value={"parsed": "local"})

        with patch.object(resume_parser.settings, "USE_LOCAL_PIPELINE", True), \
             patch.object(resume_parser, "parse_with_rules", rules_parser), \
             patch.object(resume_parser, "categorize_with_llm", cloud_llm), \
             patch.object(resume_parser, "categorize_with_local_llm", local_llm):
            structured = await resume_parser.parse_markdown_by_method("resume markdown", "rules")

        self.assertEqual(structured, {"parsed": "rules"})
        rules_parser.assert_called_once_with("resume markdown")
        cloud_llm.assert_not_awaited()
        local_llm.assert_not_awaited()

    async def test_queue_status_includes_local_pipeline_unavailable_payload(self):
        fake_db = _FakeQueueDb(rows=[])
        current_user = SimpleNamespace(id=3)
        unavailable_payload = {
            "local": {
                "available": False,
                "message": "Local AI is unavailable right now.",
            },
            "cloud": {
                "available": True,
            },
            "rules": {
                "available": True,
            },
        }

        with patch.object(resume_api.settings, "REDIS_ENABLED", False), \
             patch.object(
                 resume_api,
                 "get_pipeline_availability",
                 AsyncMock(return_value=unavailable_payload),
             ):
            payload = await resume_api._build_queue_status_payload(
                db=fake_db,
                current_user=current_user,
                scope="user",
                focus_method="local",
            )

        self.assertIn("pipeline_availability", payload)
        self.assertEqual(payload["pipeline_availability"]["local"]["available"], False)
        self.assertEqual(
            payload["pipeline_availability"]["local"]["message"],
            "Local AI is unavailable right now.",
        )
        self.assertEqual(payload["pipeline_availability"]["cloud"]["available"], True)
        self.assertEqual(payload["pipeline_availability"]["rules"]["available"], True)

    async def test_queue_status_includes_cloud_degraded_message(self):
        fake_db = _FakeQueueDb(rows=[])
        current_user = SimpleNamespace(id=3)
        availability_payload = {
            "local": {
                "available": False,
                "message": "Local AI is unavailable right now.",
            },
            "cloud": {
                "available": True,
                "degraded": True,
                "message": "Cloud AI is temporarily rate limited. UAH is retrying with provider-aware backoff.",
            },
            "rules": {
                "available": True,
            },
        }

        with patch.object(resume_api.settings, "REDIS_ENABLED", False), \
             patch.object(
                 resume_api,
                 "get_pipeline_availability",
                 AsyncMock(return_value=availability_payload),
             ):
            payload = await resume_api._build_queue_status_payload(
                db=fake_db,
                current_user=current_user,
                scope="user",
                focus_method="cloud",
            )

        self.assertEqual(payload["pipeline_availability"]["cloud"]["degraded"], True)
        self.assertIn("rate limited", payload["pipeline_availability"]["cloud"]["message"])

    async def test_cloud_llm_transient_429_retries_and_uses_configured_max_tokens(self):
        response_429 = httpx.Response(
            429,
            headers={"Retry-After": "0"},
            json={"code": "rate_limit_exceeded", "message": "too many requests"},
        )
        response_200 = httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{\"summary\": \"ok\"}"}}]},
        )
        responses = [response_429, response_200]
        request_payloads = []

        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, _url, json=None, headers=None):
                request_payloads.append({"json": json, "headers": headers})
                return responses.pop(0)

        with patch.object(resume_parser.settings, "ZAI_LLM_MAX_TOKENS", 3072), \
             patch.object(resume_parser.httpx, "AsyncClient", return_value=_FakeClient()):
            parsed = await resume_parser.categorize_with_llm("resume markdown")

        self.assertEqual(parsed["summary"], "ok")
        self.assertEqual(len(request_payloads), 2)
        self.assertEqual(request_payloads[0]["json"]["max_tokens"], 3072)

    async def test_cloud_llm_quota_429_fails_without_retry(self):
        response_429 = httpx.Response(
            429,
            json={"code": "quota_exhausted", "message": "daily quota exhausted"},
        )
        request_calls = []

        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, _url, json=None, headers=None):
                request_calls.append({"json": json, "headers": headers})
                return response_429

        with patch.object(resume_parser.httpx, "AsyncClient", return_value=_FakeClient()):
            result = await resume_parser.categorize_with_llm("resume markdown")

        self.assertEqual(result["error_code"], "CLOUD_LLM_QUOTA_EXHAUSTED")
        self.assertEqual(len(request_calls), 1)

    async def test_cloud_llm_empty_response_marks_cloud_unreliable(self):
        response_200 = httpx.Response(
            200,
            json={"choices": [{"message": {"content": ""}}]},
        )

        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, _url, json=None, headers=None):
                return response_200

        with patch.object(resume_parser.httpx, "AsyncClient", return_value=_FakeClient()):
            result = await resume_parser.categorize_with_llm("resume markdown")
            availability = resume_parser.get_cloud_provider_availability()

        self.assertEqual(result["error_code"], "LLM_EMPTY_RESPONSE")
        self.assertEqual(availability["available"], True)
        self.assertEqual(availability["unreliable"], True)
        self.assertEqual(availability["last_error_code"], "LLM_EMPTY_RESPONSE")

    async def test_parse_markdown_with_fallback_uses_local_after_cloud_empty_response(self):
        with patch.object(
            resume_parser,
            "parse_markdown_by_method",
            AsyncMock(
                side_effect=[
                    {
                        "ok": False,
                        "error_code": "LLM_EMPTY_RESPONSE",
                        "message": "AI returned no structured data. Try again or use rules-based parsing.",
                    },
                    {"parsed": "local"},
                ]
            ),
        ):
            result = await resume_parser.parse_markdown_with_fallback("resume markdown", "cloud")

        self.assertEqual(result["ok"], True)
        self.assertEqual(result["effective_method"], "local")
        self.assertEqual(result["fallback_used"], True)
        self.assertEqual(result["attempted_methods"], ["cloud", "local"])

    def test_update_review_draft_allows_persisted_review_draft_without_structured_data(self):
        resume = SimpleNamespace(
            id=101,
            user_id=7,
            file_name="resume.pdf",
            structured_data=None,
            review_draft={"personal_info": {"first_name": "Existing"}},
            review_status="pending",
            review_updated_at=None,
            parse_method="local",
        )
        fake_db = _FakeResumeByIdDb(resume)
        current_user = SimpleNamespace(id=7)
        payload = resume_api.ResumeReviewDraftUpdate(
            review_draft={"personal_info": {"first_name": "Updated"}}
        )

        response = resume_api.update_review_draft(
            payload=payload,
            resume_id=101,
            db=fake_db,
            current_user=current_user,
        )

        self.assertEqual(fake_db.commits, 1)
        self.assertEqual(resume.review_draft["personal_info"]["first_name"], "Updated")
        self.assertEqual(response.review_draft["personal_info"]["first_name"], "Updated")


if __name__ == "__main__":
    unittest.main()
