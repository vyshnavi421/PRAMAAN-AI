import os

from playwright.sync_api import expect, sync_playwright


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
