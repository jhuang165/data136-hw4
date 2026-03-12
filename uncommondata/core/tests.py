import hashlib
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from core.extraction import extract_fields_from_file
from core.models import Upload


SAMPLE_TEXT = """
C1:
Total first-time, first-year men who applied 19,195
Total first-time, first-year women who applied 23,636
Total first-time, first-year another gender who applied 0
Total first-time, first-year unknown gender who applied 781
Total first-time, first-year men who were admitted 1,070
Total first-time, first-year women who were admitted 885
Total first-time, first-year another gender who were admitted 0
Total first-time, first-year unknown gender who were admitted 0

G1:
Tuition (Undergraduates) 71,325
Required Fees: (Undergraduates) 1,941
Food and housing (on-campus): (Undergraduates) 20,835
Housing Only (on-campus): (Undergraduates) --
Food Only (on-campus meal plan): (Undergraduates) --

H2:
A. Number of degree-seeking undergraduate students 7,497
B. Number of students in line a who applied for need-based financial aid 2,953
C. Number of students in line b who were determined to have financial need 2,589
D. Number of students in line c who were awarded any financial aid 2,579
J. The average financial aid package of those in line d 78,883
"""


class UploadApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="harvester", password="pass12345")
        self.curator = User.objects.create_user(username="curator", password="pass12345")
        self.curator.profile.is_curator = True
        self.curator.profile.save()

    def test_upload_uses_sha256_id(self):
        self.client.login(username="harvester", password="pass12345")
        content = SAMPLE_TEXT.encode()
        expected_id = hashlib.sha256(content).hexdigest()

        response = self.client.post(
            "/app/api/upload/",
            {
                "institution": "UChicago",
                "year": "2024-2025",
                "file": SimpleUploadedFile("fixture.txt", content, content_type="text/plain"),
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], expected_id)
        self.assertTrue(Upload.objects.filter(pk=expected_id).exists())

    def test_download_and_process(self):
        content = SAMPLE_TEXT.encode()
        upload_id = hashlib.sha256(content).hexdigest()

        upload = Upload.objects.create(
            id=upload_id,
            user=self.user,
            institution="UChicago",
            year="2024-2025",
            file=SimpleUploadedFile("fixture.txt", content, content_type="text/plain"),
            original_filename="fixture.txt",
        )

        download = self.client.get(f"/app/api/download/{upload.id}")
        self.assertEqual(download.status_code, 200)

        process = self.client.get(f"/app/api/process/{upload.id}")
        self.assertEqual(process.status_code, 200)

        payload = process.json()
        self.assertEqual(payload["tuition_undergraduates"], 71325)
        self.assertEqual(payload["men_applied"], 19195)
        self.assertEqual(payload["average_financial_aid_package"], 78883)

    def test_show_uploads_html_contains_links(self):
        content = SAMPLE_TEXT.encode()
        upload_id = hashlib.sha256(content).hexdigest()

        upload = Upload.objects.create(
            id=upload_id,
            user=self.user,
            institution="UChicago",
            year="2024-2025",
            file=SimpleUploadedFile("fixture.txt", content, content_type="text/plain"),
            original_filename="fixture.txt",
        )

        response = self.client.get("/app/show-uploads/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"/app/api/download/{upload.id}")
        self.assertContains(response, f"/app/api/process/{upload.id}")


class ExtractionTests(TestCase):
    def test_text_extraction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "fixture.txt"
            path.write_text(SAMPLE_TEXT)
            extracted = extract_fields_from_file(str(path))

        self.assertEqual(extracted["women_applied"], 23636)
        self.assertEqual(extracted["required_fees_undergraduates"], 1941)
        self.assertIsNone(extracted["housing_only_on_campus_undergraduates"])
