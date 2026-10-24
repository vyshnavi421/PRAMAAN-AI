/**
 * PRAMAAN-AI Application Case File Dossier View
 */
import { api } from '../api.js';
import { esc } from '../util.js';
import { store } from '../state.js';

export class CaseFileView {
  constructor(container) {
    this.container = container;
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
    `;

    document.getElementById('btn-run-full-scrutiny').onclick = () => this.runPreScrutiny();
    document.getElementById('btn-reopen-run').onclick = () => this.reopenSavedRun();
    document.getElementById('btn-goto-studio').onclick = () => window.appRouter.navigate('studio');
    document.getElementById('btn-export-report').onclick = () => this.exportReport();
    document.getElementById('btn-draft-letter').onclick = () => this.draftLetter();

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

      // Render documents table
      let docRows = '';
      for (const doc of app.documents) {
        let badgeClass = 'badge-verified';
        let badgeText = doc.verification_status;
        if (doc.verification_status === 'expired') badgeClass = 'badge-expired';
        else if (doc.verification_status === 'source unavailable') badgeClass = 'badge-source-unavailable';
        else if (doc.verification_status === 'mismatch detected') badgeClass = 'badge-mismatch';

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
            <td><span class="mono-hash">${doc.sha256_hash.slice(0, 16)}...</span></td>
            <td>${doc.page_count} pg</td>
            <td><span class="badge ${badgeClass}">${badgeText}</span></td>
            <td><button class="btn btn-outline btn-sm" tabindex="-1">Inspect Evidence →</button></td>
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
              <th scope="col">Verification State</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            ${docRows}
          </tbody>
        </table>
      `;

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
