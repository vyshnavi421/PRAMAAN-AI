import os
import io
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
        expect(page.locator("#studio-app-heading")).to_contain_text("APP-", timeout=45000)
        expect(page.locator("#studio-explain-card")).to_be_visible(timeout=20000)

        page.locator("#btn-studio-mode-graph").click()
        expect(page.locator("#studio-graph-container")).to_be_visible()
        page.locator("#btn-studio-mode-pdf").click()

        screenshot_dir = Path(os.getenv("PRAMAAN_SCREENSHOT_DIR", "/tmp/pramaan-demo-artifacts"))
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_dir / "pramaan-evidence-studio.png"), full_page=True)

        deficiency = page.locator("#studio-findings-list .finding-card").filter(
            has_text="DEFICIENCY"
        )
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
    text = "Issued on: 2023-01-15 Valid until: 2024-01-14"
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 50 720 Td ({escaped}) Tj ET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
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
        application_id = page.evaluate("""async () => {
            const token = localStorage.getItem("pramaan_session_token");
            if (!token) throw new Error("The demo session was not initialized.");
            const response = await fetch("/api/v1/applications", {
                method: "POST",
                headers: {
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    institution_name: "Evidence Demo Institute",
                    institution_id: "inst-e2e-demo-001",
                    category: "EXTENSION_OF_APPROVAL",
                    academic_year: "2026-2027",
                    total_intake: 180
                })
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.detail || ("Create application failed: " + response.status));
            return payload.application_id;
        }""")
        page.evaluate("(applicationId) => window.appRouter.openCase(applicationId)", application_id)
        expect(page.locator("#cf-upload-form")).to_be_visible(timeout=20000)

        page.locator("#cf-upload-type").select_option("FIRE_SAFETY_NOC")
        page.locator("#cf-upload-file").set_input_files({
            "name": "fire_safety_noc_upload_test.pdf",
            "mimeType": "application/pdf",
            "buffer": _make_fire_safety_pdf(),
        })
        page.locator("#btn-upload-document").click()

        # Assert claims returned from real uploaded bytes, not a client-side fixture.
        feedback = page.locator("#cf-upload-feedback")
        expect(feedback).to_contain_text(
            "Upload completed — actual backend response", timeout=20000
        )
        expect(feedback).to_contain_text("noc_expiry_date", timeout=20000)
        expect(feedback).to_contain_text("2024-01-14", timeout=20000)
        expect(feedback).to_contain_text("97% confidence", timeout=20000)
        uploaded_row = page.locator("#cf-docs-table tr").filter(
            has_text="fire_safety_noc_upload_test.pdf"
        )
        expect(uploaded_row).to_contain_text("1 claim", timeout=20000)
        expect(uploaded_row).to_contain_text("2024-01-14")
        document_id = uploaded_row.locator("button[data-view-document]").get_attribute("data-view-document")

        # Render the actual PDF page and prove that the normalized extraction box is drawn
        # over it. CI installs Poppler explicitly so this check is reproducible.
        uploaded_row.get_by_role("button", name="View p. 1").click()
        expect(page.locator("#cf-page-view-image")).to_be_visible(timeout=20000)
        expect(page.locator("#cf-page-view-status")).to_contain_text(
            "claim bounding box(es) highlighted", timeout=20000
        )
        expect(page.locator("#cf-page-view-overlay rect[data-field-key='noc_expiry_date']")).to_have_count(1)
        expect(page.locator("#cf-page-view-legend")).to_contain_text("noc_expiry_date")
        page.locator("#btn-close-page-viewer").click()

        # Continue the same document through the end-to-end scrutiny story:
        # extracted evidence -> rule finding -> simulated issuer check -> human decision -> audit.
        page.locator("#btn-run-full-scrutiny").click()
        expect(page.locator("#studio-app-heading")).to_contain_text("APP-", timeout=45000)
        finding = page.locator("#studio-findings-list .finding-card").filter(
            has_text="RULE-APH-EXP-003"
        )
        expect(finding).to_be_visible(timeout=20000)
        expect(finding).to_contain_text("DEFICIENCY")
        finding.click()
        expect(page.locator("#studio-explain-card")).to_contain_text("2024-01-14", timeout=15000)

        page.locator('button[data-route="verification"]').click()
        expect(page.locator("#select-document")).to_be_visible(timeout=20000)
        page.locator("#select-document").select_option(document_id)
        page.locator("#select-fixture").select_option("FIX-EXPIRED")
        page.locator("#btn-execute-verify").click()
        expect(page.locator("#result-status-badge")).to_have_text("EXPIRED", timeout=20000)
        expect(page.locator(".page-header")).to_contain_text("DEMO / SIMULATED MODE")

        # The issuer check is simulated. Return to the same finding and record a human decision.
        page.locator('button[data-route="studio"]').click()
        expect(page.locator("#studio-app-heading")).to_contain_text("APP-", timeout=20000)
        finding = page.locator("#studio-findings-list .finding-card").filter(
            has_text="RULE-APH-EXP-003"
        )
        expect(finding).to_be_visible(timeout=15000)
        finding.click()
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

        # Exercise the protected page-view endpoint for a raster image too.
        png_buffer = io.BytesIO()
        Image.new("RGB", (8, 8), color=(240, 240, 240)).save(png_buffer, format="PNG")
        page.locator("#cf-upload-type").select_option("LAND_USE_CERTIFICATE")
        page.locator("#cf-upload-file").set_input_files({
            "name": "scan_upload_test.png",
            "mimeType": "image/png",
            "buffer": png_buffer.getvalue(),
        })
        page.locator("#btn-upload-document").click()
        expect(feedback).to_contain_text(
            "Upload completed — actual backend response", timeout=20000
        )
        png_row = page.locator("#cf-docs-table tr").filter(has_text="scan_upload_test.png")
        expect(png_row).to_be_visible(timeout=20000)
        png_row.get_by_role("button", name="View p. 1").click()
        expect(page.locator("#cf-page-view-image")).to_be_visible(timeout=20000)
        expect(page.locator("#cf-page-view-status")).to_contain_text(
            "rendered from the actual uploaded document bytes"
        )
        browser.close()
