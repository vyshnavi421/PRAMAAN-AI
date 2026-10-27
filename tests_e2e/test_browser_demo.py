import os
import io
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from PIL import Image


BASE_URL = os.getenv("PRAMAAN_BASE_URL", "http://127.0.0.1:8000")


def test_demo_entry_and_review_path():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(BASE_URL, wait_until="domcontentloaded")

        expect(page.locator("#health-indicator-text")).to_contain_text(
            "Backend: Operational", timeout=30000
        )
        expect(page.locator(".demo-pill")).to_contain_text("DEMO DATA")

        page.locator(
            '[aria-label="Open Bundle 02: Greenfield College of Engg, Expired NOC"]'
        ).click()
        expect(page.locator("#cf-title")).to_contain_text("APP-", timeout=20000)
        page.locator("#btn-run-full-scrutiny").click()
        expect(page.locator("#studio-app-heading")).to_contain_text(
            "APP-", timeout=45000
        )
        expect(page.locator("#studio-explain-card")).to_be_visible(timeout=20000)

        page.locator("#btn-studio-mode-graph").click()
        expect(page.locator("#studio-graph-container")).to_be_visible()
        page.locator("#btn-studio-mode-pdf").click()

        screenshot_dir = Path(
            os.getenv("PRAMAAN_SCREENSHOT_DIR", "/tmp/pramaan-demo-artifacts")
        )
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(
            path=str(screenshot_dir / "pramaan-evidence-studio.png"),
            full_page=True,
        )

        deficiency = page.locator(
            "#studio-findings-list .finding-card"
        ).filter(has_text="DEFICIENCY")
        expect(deficiency.first).to_be_visible(timeout=15000)
        deficiency.first.click()
        page.locator("#btn-studio-open-decision").click()
        expect(page.locator("#decision-modal")).to_be_visible()
        page.locator("#btn-modal-submit").click()
        expect(page.locator("#toast-container")).to_contain_text(
            "committed to cryptographic audit ledger", timeout=20000
        )

        page.locator('button[data-route="audit"]').click()
        expect(page.locator("#audit-table-body")).to_contain_text(
            "REVIEW_ACTION_CONFIRM_DEFICIENCY", timeout=20000
        )
        page.locator("#btn-verify-chain-now").click()
        expect(page.locator("#chain-status-text")).to_contain_text(
            "Cryptographic Audit Chain Intact", timeout=20000
        )
        browser.close()


def test_reviewer_queue_is_populated():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(BASE_URL, wait_until="domcontentloaded")

        expect(page.locator("#health-indicator-text")).to_contain_text(
            "Backend: Operational", timeout=30000
        )
        page.locator('button[data-route="queue"]').click()
        expect(page.locator("h1.page-title")).to_have_text(
            "Scrutiny Officer Work Queue", timeout=15000
        )
        expect(
            page.get_by_role("table", name="Assigned Institutional Applications")
        ).to_be_visible(timeout=15000)
        expect(page.locator("#queue-count-badge")).to_contain_text("Showing")
        browser.close()


def _make_fire_safety_pdf() -> bytes:
    """Build a tiny valid PDF carrying a real expiry-date text claim for the demo test."""
    text = "Valid until: 2027-06-30"
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 50 720 Td ({escaped}) Tj ET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def test_real_document_upload_extracts_and_displays_source_claim():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(BASE_URL, wait_until="domcontentloaded")

        expect(page.locator("#health-indicator-text")).to_contain_text(
            "Backend: Operational", timeout=30000
        )
        page.evaluate("window.appRouter.openCase('app-case-clean')")
        expect(page.locator("#cf-upload-form")).to_be_visible(timeout=20000)

        page.locator("#cf-upload-type").select_option("FIRE_SAFETY_NOC")

        # Generate a unique filename for every test run.
        upload_filename = f"fire_safety_noc_upload_test_{uuid.uuid4().hex}.pdf"

        page.locator("#cf-upload-file").set_input_files({
            "name": upload_filename,
            "mimeType": "application/pdf",
            "buffer": _make_fire_safety_pdf(),
        })
        page.locator("#btn-upload-document").click()

        # Verify the actual backend response and extracted claim.
        feedback = page.locator("#cf-upload-feedback")
        expect(feedback).to_contain_text(
            "Upload completed — actual backend response", timeout=20000
        )
        expect(feedback).to_contain_text("noc_expiry_date", timeout=20000)
        expect(feedback).to_contain_text("2027-06-30", timeout=20000)
        expect(feedback).to_contain_text("97% confidence", timeout=20000)

        # Match the exact unique filename uploaded in this test.
        uploaded_row = page.locator("#cf-docs-table tr").filter(
            has_text=upload_filename
        )
        expect(uploaded_row).to_contain_text("1 claim", timeout=20000)
        expect(uploaded_row).to_contain_text("2027-06-30")

        # Test the protected page-view endpoint using an actual PNG image.
        # This avoids depending on Poppler being installed on the CI runner.
        png_buffer = io.BytesIO()
        Image.new("RGB", (8, 8), color=(240, 240, 240)).save(
            png_buffer, format="PNG"
        )

        # Generate a unique PNG filename for each test run.
        png_filename = f"scan_upload_test_{uuid.uuid4().hex}.png"

        page.locator("#cf-upload-type").select_option("LAND_USE_CERTIFICATE")
        page.locator("#cf-upload-file").set_input_files({
            "name": png_filename,
            "mimeType": "image/png",
            "buffer": png_buffer.getvalue(),
        })
        page.locator("#btn-upload-document").click()

        expect(feedback).to_contain_text(
            "Upload completed — actual backend response", timeout=20000
        )

        png_row = page.locator("#cf-docs-table tr").filter(
         has_text=png_filename
        )
        expect(png_row).to_be_visible(timeout=20000)
        png_row.get_by_role("button", name="View p. 1").click()

        expect(page.locator("#cf-page-view-image")).to_be_visible(timeout=20000)
        expect(page.locator("#cf-page-view-status")).to_contain_text(
            "rendered from the actual uploaded document bytes"
        )

        browser.close()
