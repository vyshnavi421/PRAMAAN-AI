/**
 * PRAMAAN-AI Application Case File Dossier View
 */
import { api } from '../api.js';
import { esc } from '../util.js';
import { store } from '../state.js';

export class CaseFileView {
  constructor(container) {
    this.container = container;
    this.pageObjectUrl = null;
  }

  async render() {
    const s = store.getState();
    const appId = s.activeApplicationId;

    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--cobalt-600); margin-bottom: 2px;">
            Application Case File Dossier
          </div>
          <h1 id="cf-title" class="page-title">Loading Dossier...</h1>
          <p id="cf-meta" class="page-desc">Retrieving uploaded documents and institutional declarations...</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button id="btn-run-full-scrutiny" class="btn btn-primary">
            ⚡ Run Complete Pre-Scrutiny
          </button>
          <button id="btn-reopen-run" class="btn btn-outline">
            Reopen Saved Run
          </button>
          <button id="btn-goto-studio" class="btn btn-outline">
            Evidence Studio →
          </button>
          <button id="btn-export-report" class="btn btn-outline" title="Open printable report (use Print → Save as PDF)">
            📄 Report
          </button>
          <button id="btn-draft-letter" class="btn btn-outline" title="Draft clarification letter for officer approval">
            ✉ Draft Letter
          </button>
        </div>
      </div>

      <!-- Dossier Summary Info Cards -->
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-label">Declared Intake</span>
          <span id="cf-intake" class="metric-val">180</span>
          <span class="metric-meta">Approved AICTE Baseline</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Uploaded Documents</span>
          <span id="cf-doc-count" class="metric-val">4</span>
          <span class="metric-meta">PDF & Scan Assets</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Submission Date</span>
          <span id="cf-sub-date" class="metric-val" style="font-size: 18px;">2026-04-10</span>
          <span class="metric-meta">Cutoff: 2026-06-30</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Coverage Audit Status</span>
          <span id="cf-coverage-status" class="metric-val" style="font-size: 16px; color: var(--slate-500);">Awaiting Run</span>
          <span class="metric-meta">Independent Reconciliation</span>
        </div>
      </div>

      <!-- Secure Document Intake -->
      <div class="table-card" style="margin-bottom: var(--space-5);">
        <div class="table-toolbar">
          <div>
            <span style="font-weight: 700; font-size: 14px; color: var(--navy-950);">Secure Document Intake</span>
            <div style="font-size: 11px; color: var(--slate-500);">Upload a real file to store its bytes, calculate SHA-256, and extract supported claims.</div>
          </div>
          <span class="badge badge-pending">MAX 25 MB</span>
        </div>
        <form id="cf-upload-form" style="padding: 16px;" novalidate>
          <div style="display: grid; grid-template-columns: minmax(220px, 0.8fr) minmax(280px, 1.5fr); gap: 14px; align-items: end;">
            <div>
              <label for="cf-upload-type" style="display: block; font-size: 12px; font-weight: 700; color: var(--slate-700); margin-bottom: 6px;">Document type</label>
              <select id="cf-upload-type" name="document_type" required style="width: 100%; min-height: 38px; border: 1px solid var(--slate-300); border-radius: var(--radius-md); padding: 8px 10px; background: var(--white); color: var(--slate-800);">
                <option value="FIRE_SAFETY_NOC">Fire Safety NOC</option>
                <option value="AFFIDAVIT_GENERAL">General Affidavit</option>
                <option value="LAND_USE_CERTIFICATE">Land Use Certificate</option>
                <option value="BUILDING_PLAN_ARCHITECT">Architect Building Plan</option>
                <option value="GOVERNING_BODY_RESOLUTION">Governing Body Resolution</option>
                <option value="AICTE_PREVIOUS_EOA">Previous AICTE EoA</option>
                <option value="LAND_CONVERSION_ORDER">Land Conversion Order</option>
              </select>
            </div>
            <div>
              <label for="cf-upload-file" style="display: block; font-size: 12px; font-weight: 700; color: var(--slate-700); margin-bottom: 6px;">Choose a document</label>
              <input id="cf-upload-file" name="file" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" required style="width: 100%; min-height: 38px; border: 1px solid var(--slate-300); border-radius: var(--radius-md); padding: 6px 8px; background: var(--white); color: var(--slate-800);">
            </div>
          </div>
          <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 14px;">
            <button id="btn-upload-document" class="btn btn-primary" type="submit">Upload &amp; Extract</button>
            <span id="cf-upload-selected" style="font-size: 12px; color: var(--slate-500);">PDF, JPEG, or PNG. Maximum 25 MB.</span>
          </div>
          <p style="font-size: 11px; color: var(--slate-500); line-height: 1.5; margin: 10px 0 0;">
            The server validates the file signature and size. Extraction runs on the uploaded bytes; unreadable files are not given fabricated claims and may require manual review. Only institution users and reviewers can upload.
          </p>
          <div id="cf-upload-feedback" role="status" aria-live="polite" hidden style="margin-top: 14px; padding: 12px; border: 1px solid var(--slate-200); border-radius: var(--radius-md); background: var(--slate-50); color: var(--slate-800);"></div>
        </form>
      </div>

      <!-- Uploaded Document Inventory Table -->
      <div class="table-card">
        <div class="table-toolbar">
          <div>
            <span style="font-weight: 700; font-size: 14px; color: var(--navy-950);">Document Inventory & Cryptographic Fingerprints</span>
            <div style="font-size: 11px; color: var(--slate-500);">Ground-truth binary files stored in protected isolation</div>
          </div>
          <span id="cf-doc-badge" class="badge badge-verified">4 DOCUMENTS LOADED</span>
        </div>
        <div id="cf-docs-table" style="overflow-x: auto;">
          <div style="padding: 16px;">
            <div class="skeleton-row">
              <span class="skeleton" style="width: 160px; height: 16px;"></span>
              <span class="skeleton" style="width: 200px; height: 16px;"></span>
              <span class="skeleton" style="width: 180px; height: 16px;"></span>
              <span class="skeleton" style="width: 50px; height: 16px;"></span>
              <span class="skeleton" style="width: 120px; height: 16px;"></span>
              <span class="skeleton" style="width: 100px; height: 16px;"></span>
            </div>
            <div class="skeleton-row">
              <span class="skeleton" style="width: 160px; height: 16px;"></span>
              <span class="skeleton" style="width: 200px; height: 16px;"></span>
              <span class="skeleton" style="width: 180px; height: 16px;"></span>
              <span class="skeleton" style="width: 50px; height: 16px;"></span>
              <span class="skeleton" style="width: 120px; height: 16px;"></span>
              <span class="skeleton" style="width: 100px; height: 16px;"></span>
            </div>
          </div>
        </div>
      </div>
      <div id="cf-page-viewer" class="table-card" hidden style="margin-top: var(--space-5);">
        <div class="table-toolbar">
          <div>
            <span style="font-weight: 700; font-size: 14px; color: var(--navy-950);">Uploaded Document — Real Page Preview</span>
            <div style="font-size: 11px; color: var(--slate-500);">Rendered from the protected stored file; seeded demo placeholders have no uploaded binary.</div>
          </div>
          <button id="btn-close-page-viewer" class="btn btn-outline btn-sm" type="button">Close preview</button>
        </div>
        <div id="cf-page-view-status" role="status" aria-live="polite" style="padding: 12px; color: var(--slate-600);">Choose “View p. 1” on a real uploaded file.</div>
        <div style="padding: 0 16px 16px; overflow: auto; text-align: center;">
          <img id="cf-page-view-image" alt="Rendered page from the uploaded institutional document" hidden style="max-width: 100%; height: auto; border: 1px solid var(--slate-200); border-radius: var(--radius-md); box-shadow: var(--shadow-sm);">
        </div>
      </div>
    `;

    document.getElementById('btn-run-full-scrutiny').onclick = () => this.runPreScrutiny();
    document.getElementById('btn-reopen-run').onclick = () => this.reopenSavedRun();
    document.getElementById('btn-goto-studio').onclick = () => window.appRouter.navigate('studio');
    document.getElementById('btn-export-report').onclick = () => this.exportReport();
    document.getElementById('btn-draft-letter').onclick = () => this.draftLetter();
    document.getElementById('cf-upload-form').addEventListener('submit', (event) => {
      event.preventDefault();
      this.uploadSelectedDocument();
    });
    document.getElementById('cf-upload-file').addEventListener('change', (event) => {
      const file = event.target.files?.[0];
      document.getElementById('cf-upload-selected').textContent = file
        ? `${file.name} · ${(file.size / (1024 * 1024)).toFixed(2)} MB`
        : 'PDF, JPEG, or PNG. Maximum 25 MB.';
    });

    await this.loadDossierData(appId);
  }

  async loadDossierData(appId) {
    try {
      const res = await api.getApplication(appId);
      const app = res.data;
      store.setState({ activeApplicationData: app });

      const instName = app.declared_data?.institution_name || app.reference_record?.legal_name || 'Technical Institute';
      document.getElementById('cf-title').textContent = `${app.application_number} — ${instName}`;
      document.getElementById('cf-meta').textContent = `Category: ${app.category} • Academic Year: ${app.academic_year} • Institution ID: ${app.institution_id}`;
      document.getElementById('cf-intake').textContent = app.declared_data?.total_intake || app.reference_record?.approved_intake || 'N/A';
      document.getElementById('cf-doc-count').textContent = app.documents.length;
      document.getElementById('cf-sub-date').textContent = app.submission_date;
      document.getElementById('cf-doc-badge').textContent = `${app.documents.length} DOCUMENTS LOADED`;

      // Render documents table from the server-returned dossier.
      let docRows = '';
      for (const doc of app.documents || []) {
        const status = String(doc.verification_status || 'verification pending');
        const statusClasses = {
          'expired': 'badge-expired',
          'source unavailable': 'badge-source-unavailable',
          'mismatch detected': 'badge-mismatch',
          'verification pending': 'badge-pending',
          'manual review required': 'badge-manual-review'
        };
        const badgeClass = statusClasses[status] || 'badge-verified';
        const claims = Array.isArray(doc.extracted_fields) ? doc.extracted_fields : [];
        const canReextract = String(doc.storage_key || '').startsWith('storage/protected/');
        const actionButton = canReextract
          ? `<div style="display: flex; gap: 6px; flex-wrap: wrap;">
              <button class="btn btn-outline btn-sm" type="button" data-view-document="${esc(doc.id)}">View p. 1</button>
              <button class="btn btn-outline btn-sm" type="button" data-extract-document="${esc(doc.id)}">Re-extract</button>
            </div>`
          : '<button class="btn btn-outline btn-sm" type="button" tabindex="-1">Inspect Evidence →</button>';
        const claimsSummary = claims.length
          ? `<div style="font-size: 11px; color: var(--slate-500);">${claims.length} claim${claims.length === 1 ? '' : 's'}</div>
             <div style="font-size: 11px; line-height: 1.4; margin-top: 4px;">${claims.slice(0, 2).map((field) => {
               const confidence = Number.isFinite(Number(field.confidence))
                 ? ` · ${Math.round(Number(field.confidence) * 100)}%`
                 : '';
               return `<div><code>${esc(field.field_key)}</code>: <strong>${esc(field.field_value)}</strong><span style="color: var(--slate-500);">${confidence}</span></div>`;
             }).join('')}${claims.length > 2 ? `<div style="color: var(--slate-500);">+${claims.length - 2} more</div>` : ''}</div>`
          : 'No fields extracted';

        docRows += `
          <tr
            style="cursor: pointer;"
            tabindex="0"
            role="link"
            aria-label="Inspect ${esc(doc.document_type)} ${esc(doc.original_filename)}"
            onclick="window.appRouter.navigate('studio')"
            onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault(); window.appRouter.navigate('studio');}"
          >
            <td><strong>${esc(doc.document_type)}</strong></td>
            <td>${esc(doc.original_filename)}</td>
            <td><span class="mono-hash" title="${esc(doc.sha256_hash || '')}">${esc(String(doc.sha256_hash || 'Unavailable').slice(0, 16))}...</span></td>
            <td>${esc(String(doc.page_count || '—'))} pg</td>
            <td>${claimsSummary}</td>
            <td><span class="badge ${badgeClass}">${esc(status)}</span></td>
            <td>${actionButton}</td>
          </tr>
        `;
      }

      document.getElementById('cf-docs-table').innerHTML = `
        <table class="data-table" role="table" aria-label="Application Document Inventory">
          <thead>
            <tr>
              <th scope="col">Document Type</th>
              <th scope="col">Filename</th>
              <th scope="col">SHA-256 Hash</th>
              <th scope="col">Pages</th>
              <th scope="col">Extracted Claims</th>
              <th scope="col">Verification State</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            ${docRows || '<tr><td colspan="7" style="padding: 20px; color: var(--slate-500);">No documents are attached to this application yet.</td></tr>'}
          </tbody>
        </table>
      `;

      document.querySelectorAll('#cf-docs-table [data-extract-document]').forEach((button) => {
        button.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          this.extractDocument(button.dataset.extractDocument, button);
        });
      });
      document.querySelectorAll('#cf-docs-table [data-view-document]').forEach((button) => {
        button.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          this.viewDocumentPage(button.dataset.viewDocument, 1, button);
        });
      });
      document.getElementById('btn-close-page-viewer')?.addEventListener('click', () => {
        const panel = document.getElementById('cf-page-viewer');
        const image = document.getElementById('cf-page-view-image');
        if (image) { image.removeAttribute('src'); image.hidden = true; }
        if (panel) panel.hidden = true;
        const status = document.getElementById('cf-page-view-status');
        if (status) status.textContent = 'Preview closed.';
        if (this.pageObjectUrl) URL.revokeObjectURL(this.pageObjectUrl);
        this.pageObjectUrl = null;
      });

      // Check if a saved review run already exists
      try {
        const latestRes = await api.getLatestReviewReport(appId);
        if (latestRes.data) {
          store.setState({ activeReviewReport: latestRes.data });
          const cov = latestRes.data.coverage_audit;
          if (cov.is_complete === false) {
            document.getElementById('cf-coverage-status').textContent = `${cov.coverage_percentage}% INCOMPLETE`;
            document.getElementById('cf-coverage-status').style.color = 'var(--severity-deficiency-fg)';
          } else {
            document.getElementById('cf-coverage-status').textContent = '100% COMPLETE';
            document.getElementById('cf-coverage-status').style.color = 'var(--severity-compliant-fg)';
          }
        }
      } catch (_) {}

    } catch (err) {
      document.getElementById('cf-title').textContent = "Failed to load dossier";
      document.getElementById('cf-meta').textContent = err.message;
      document.getElementById('cf-docs-table').innerHTML = `
        <div style="padding: 24px;">
          <div class="error-card">
            <svg width="22" height="22" fill="currentColor" viewBox="0 0 20 20" style="flex-shrink: 0; color: var(--severity-deficiency-fg);">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
            <div>
              <div class="error-card-title">Dossier Retrieval Failed (RFC 7807 Error)</div>
              <div class="error-card-detail">${esc(err.message)}</div>
              <div class="error-card-meta">Instance: /api/v1/applications/${appId}</div>
              <button class="btn btn-primary btn-sm" style="margin-top: 12px;" onclick="window.appRouter.views['case-file'].loadDossierData('${appId}')">Retry</button>
            </div>
          </div>
        </div>
      `;
    }
  }

  showUploadMessage(message, tone = 'info') {
    const panel = document.getElementById('cf-upload-feedback');
    if (!panel) return;
    panel.hidden = false;
    panel.replaceChildren();
    panel.textContent = message;
    panel.style.borderColor = tone === 'danger'
      ? 'var(--severity-deficiency-border)'
      : tone === 'warning'
        ? 'var(--severity-anomaly-border)'
        : 'var(--slate-200)';
    panel.style.backgroundColor = tone === 'danger'
      ? 'var(--severity-deficiency-bg)'
      : tone === 'warning'
        ? 'var(--severity-anomaly-bg)'
        : 'var(--slate-50)';
    panel.style.color = tone === 'danger'
      ? 'var(--severity-deficiency-fg)'
      : tone === 'warning'
        ? 'var(--severity-anomaly-fg)'
        : 'var(--slate-800)';
  }

  renderUploadResult(doc, heading = 'Server processing result') {
    const panel = document.getElementById('cf-upload-feedback');
    if (!panel) return;
    const fields = Array.isArray(doc.extracted_fields) ? doc.extracted_fields : [];
    const status = String(doc.verification_status || 'verification pending');
    const details = fields.length
      ? `<ul style="margin: 8px 0 0; padding-left: 20px;">${fields.map((field) => {
          const confidence = Number.isFinite(Number(field.confidence))
            ? `${Math.round(Number(field.confidence) * 100)}% confidence`
            : 'confidence not provided';
          const page = field.provenance?.page_number ? ` · page ${esc(String(field.provenance.page_number))}` : '';
          const snippet = field.provenance?.surrounding_snippet || field.raw_value || '';
          return `<li style="margin-top: 6px;"><code>${esc(field.field_key)}</code>: <strong>${esc(field.field_value)}</strong> <span style="color: var(--slate-500);">(${confidence}${page})</span><div style="font-size: 11px; color: var(--slate-500); margin-top: 2px;">Source: ${esc(snippet)}</div></li>`;
        }).join('')}</ul>`
      : '<p style="font-size: 12px; margin: 8px 0 0;">No fields were extracted from this file. No claims were fabricated; review the status below and manually inspect the document when needed.</p>';

    panel.hidden = false;
    panel.style.borderColor = status === 'manual review required'
      ? 'var(--status-manual-review-border)'
      : 'var(--slate-200)';
    panel.style.backgroundColor = status === 'manual review required'
      ? 'var(--status-manual-review-bg)'
      : 'var(--slate-50)';
    panel.style.color = 'var(--slate-800)';
    panel.innerHTML = `
      <div style="font-weight: 700; color: var(--navy-950);">${esc(heading)}</div>
      <div style="font-size: 12px; margin-top: 6px;">File: <strong>${esc(doc.original_filename || 'Uploaded document')}</strong></div>
      <div style="font-size: 12px; margin-top: 4px;">Server status: <strong>${esc(status)}</strong> · SHA-256: <code>${esc(doc.sha256_hash || 'not returned')}</code></div>
      <div style="font-size: 12px; margin-top: 4px;">Extracted claims: <strong>${fields.length}</strong></div>
      ${details}
    `;
  }

  async viewDocumentPage(documentId, pageNumber = 1, button = null) {
    const panel = document.getElementById('cf-page-viewer');
    const status = document.getElementById('cf-page-view-status');
    const image = document.getElementById('cf-page-view-image');
    if (!panel || !status || !image) return;

    panel.hidden = false;
    image.hidden = true;
    status.textContent = 'Requesting the real stored page from the protected API…';
    if (button) { button.disabled = true; button.textContent = 'Loading…'; }
    try {
      const blob = await api.getDocumentPageView(documentId, pageNumber);
      if (!blob.type.startsWith('image/')) {
        throw new Error('The page endpoint did not return an image.');
      }
      if (this.pageObjectUrl) URL.revokeObjectURL(this.pageObjectUrl);
      this.pageObjectUrl = URL.createObjectURL(blob);
      image.src = this.pageObjectUrl;
      image.hidden = false;
      status.textContent = `Page ${pageNumber} rendered from the actual uploaded document bytes.`;
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      status.textContent = `Page preview unavailable: ${err.message}. This does not affect stored claims or verification status.`;
      window.appToast.show(`Page preview unavailable: ${err.message}`, 'warning');
    } finally {
      if (button?.isConnected) {
        button.disabled = false;
        button.textContent = 'View p. 1';
      }
    }
  }

  async uploadSelectedDocument() {
    const app = store.getState().activeApplicationData;
    const fileInput = document.getElementById('cf-upload-file');
    const typeInput = document.getElementById('cf-upload-type');
    const submit = document.getElementById('btn-upload-document');
    const file = fileInput?.files?.[0];

    if (!app?.application_id) {
      this.showUploadMessage('Load an application dossier before uploading a document.', 'warning');
      return;
    }
    if (!file) {
      this.showUploadMessage('Choose a PDF, JPEG, or PNG file first.', 'warning');
      fileInput?.focus();
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      this.showUploadMessage('This file exceeds the 25 MB upload limit. Choose a smaller file.', 'warning');
      return;
    }

    submit.disabled = true;
    submit.textContent = 'Uploading & extracting…';
    this.showUploadMessage('Uploading file bytes to the protected document endpoint and processing the server response…');

    try {
      const res = await api.uploadDocument(file, typeInput.value, app.application_id);
      const doc = res.data;
      fileInput.value = '';
      document.getElementById('cf-upload-selected').textContent = 'PDF, JPEG, or PNG. Maximum 25 MB.';
      this.renderUploadResult(doc, 'Upload completed — actual backend response');
      await this.loadDossierData(app.application_id);
      this.renderUploadResult(doc, 'Upload completed — actual backend response');
      window.appToast.show(
        `Uploaded ${doc.original_filename}: ${(doc.extracted_fields || []).length} claim(s); status: ${doc.verification_status}.`,
        doc.verification_status === 'manual review required' ? 'warning' : 'info'
      );
    } catch (err) {
      this.showUploadMessage(`Upload failed: ${err.message}. The server remains responsible for file signature, type, permission, and size validation.`, 'danger');
      window.appToast.show(`Document upload failed: ${err.message}`, 'danger');
    } finally {
      submit.disabled = false;
      submit.textContent = 'Upload & Extract';
    }
  }

  async extractDocument(documentId, button = null) {
    if (button) {
      button.disabled = true;
      button.textContent = 'Extracting…';
    }
    try {
      const res = await api.extractDocument(documentId);
      const doc = res.data;
      this.renderUploadResult(doc, 'Re-extraction completed — actual backend response');
      await this.loadDossierData(store.getState().activeApplicationId);
      this.renderUploadResult(doc, 'Re-extraction completed — actual backend response');
      window.appToast.show(
        `Re-extraction finished: ${(doc.extracted_fields || []).length} claim(s); status: ${doc.verification_status}.`,
        doc.verification_status === 'manual review required' ? 'warning' : 'info'
      );
    } catch (err) {
      this.showUploadMessage(`Extraction failed: ${err.message}`, 'danger');
      window.appToast.show(`Document extraction failed: ${err.message}`, 'danger');
    } finally {
      if (button?.isConnected) {
        button.disabled = false;
        button.textContent = 'Re-extract';
      }
    }
  }

  async runPreScrutiny() {
    const s = store.getState();
    const app = s.activeApplicationData;
    if (!app) return;

    const btn = document.getElementById('btn-run-full-scrutiny');
    btn.disabled = true;
    btn.textContent = 'Executing Pre-Scrutiny...';

    try {
      const res = await api.runFullReview(app.application_id);
      const report = res.data;
      store.setState({ activeReviewReport: report, lastLatencyMs: res.elapsed });

      const cov = report.coverage_audit;
      if (cov.is_complete === false) {
        document.getElementById('cf-coverage-status').textContent = `${cov.coverage_percentage}% INCOMPLETE`;
        document.getElementById('cf-coverage-status').style.color = 'var(--severity-deficiency-fg)';
        window.appToast.show(`Coverage Audit Alert: Review incomplete (${cov.total_accounted}/${cov.total_planned} accounted)!`, 'warning');
      } else {
        document.getElementById('cf-coverage-status').textContent = `${cov.coverage_percentage}% COMPLETE`;
        document.getElementById('cf-coverage-status').style.color = 'var(--severity-compliant-fg)';
        window.appToast.show(`Pre-Scrutiny completed in ${res.elapsed} ms with 100% Coverage Audit Guarantee!`);
      }

      // Transition to Evidence Studio to inspect findings
      setTimeout(() => {
        window.appRouter.navigate('studio');
      }, 500);
    } catch (err) {
      window.appToast.show(`Pre-Scrutiny Error: ${err.message}`, 'danger');
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ Run Complete Pre-Scrutiny';
    }
  }

  async exportReport() {
    const id = store.getState().activeApplicationId;
    try {
      const html = await api.getScrutinyReportHtml(id);
      const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) {
      window.appToast.show(`Report unavailable: ${err.message}. Run pre-scrutiny first.`, 'warning');
    }
  }

  async draftLetter() {
    const id = store.getState().activeApplicationId;
    try {
      const text = await api.getDeficiencyLetterText(id);
      const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
      const a = document.createElement('a');
      a.href = url; a.download = `draft-letter-${id}.txt`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      window.appToast.show('Draft letter downloaded — requires officer approval before issue.');
    } catch (err) {
      window.appToast.show(`Letter unavailable: ${err.message}`, 'warning');
    }
  }

  async reopenSavedRun() {
    const s = store.getState();
    try {
      const res = await api.getLatestReviewReport(s.activeApplicationId);
      store.setState({ activeReviewReport: res.data });
      window.appToast.show(`Reopened saved pre-scrutiny run (${res.data.review_id.slice(0, 8)}...)`);
      window.appRouter.navigate('studio');
    } catch (err) {
      window.appToast.show(`No saved run found. Run pre-scrutiny first.`, 'warning');
    }
  }
}
