
/**
 * PRAMAAN-AI Institution Pre-Flight Diagnostic
 * Frontend controller connected to the existing API.
 */

import { api } from '../api.js';
import { store } from '../state.js';

const DOCUMENT_TYPES = [
  {
    type: 'AFFIDAVIT_GENERAL',
    name: 'Affidavit Format A-100',
    format: '₹100 non-judicial stamp paper notarized'
  },
  {
    type: 'FIRE_SAFETY_NOC',
    name: 'Fire Safety NOC',
    format: 'State Fire & Emergency Services certificate'
  },
  {
    type: 'LAND_USE_CERTIFICATE',
    name: 'Land Use Certificate',
    format: 'Issued by Competent Revenue Authority'
  },
  {
    type: 'BUILDING_PLAN_ARCHITECT',
    name: 'Architect Area Certificate',
    format: 'Signed by a registered architect'
  },
  {
    type: 'GOVERNING_BODY_RESOLUTION',
    name: 'Governing Body Resolution',
    format: 'Trust/Society resolution approving proposed intake'
  }
];

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[char]);
}

function formatFileSize(bytes) {
  if (bytes == null || Number.isNaN(Number(bytes))) {
    return '';
  }

  const size = Number(bytes);

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export class InstitutionPreflightView {
  constructor(container) {
    this.container = container;
    this.application = null;
    this.uploadingTypes = new Set();
  }

  async render() {
    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <div style="
            font-size:11px;
            text-transform:uppercase;
            font-weight:700;
            color:var(--cobalt-600);
            margin-bottom:2px
          ">
            Applicant Portal • Pre-Submission Diagnostic
          </div>

          <h1 class="page-title">
            Institution Pre-Flight Compliance Diagnostic
          </h1>

          <p class="page-desc">
            Review your application documents and run the available
            compliance checks.
          </p>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button id="btn-run-preflight" class="btn btn-primary">
            Run Pre-Flight Diagnostic
          </button>

          <button
            id="btn-submit-formal"
            class="btn btn-outline"
            disabled
            title="Formal submission is not connected on this page"
          >
            Formal Submit to AICTE
          </button>
        </div>
      </div>

      <div
        id="preflight-message"
        role="status"
        aria-live="polite"
        style="
          display:none;
          padding:12px 16px;
          border-radius:8px;
          margin-bottom:16px;
          white-space:pre-wrap;
          overflow-wrap:anywhere
        "
      ></div>

      <div
        id="preflight-results-banner"
        style="
          display:none;
          padding:18px;
          border-radius:var(--radius-md);
          margin-bottom:20px
        "
      ></div>

      <div class="table-card">
        <div class="table-toolbar">
          <div>
            <span style="
              font-weight:700;
              font-size:14px;
              color:var(--navy-950)
            ">
              Mandatory EoA Document Checklist
            </span>

            <div style="font-size:11px;color:var(--slate-500)">
              Documents for the selected application
            </div>
          </div>

          <span id="preflight-doc-count" class="badge">
            Loading documents...
          </span>
        </div>

        <div style="overflow-x:auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Document Type</th>
                <th>Prescribed Format</th>
                <th>Uploaded File</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody id="preflight-document-rows">
              <tr>
                <td colspan="5">
                  Loading documents from the backend...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;

    this.container
      .querySelector('#btn-run-preflight')
      .addEventListener('click', () => this.runPreflight());

    await this.loadApplicationDocuments();
  }

  getApplicationId() {
    return store.getState().activeApplicationId;
  }

  showMessage(message, type = 'info') {
    const element = this.container.querySelector('#preflight-message');

    if (!element) return;

    const colors = {
      info: ['#eff6ff', '#1d4ed8'],
      success: ['#f0fdf4', '#166534'],
      warning: ['#fffbeb', '#92400e'],
      error: ['#fef2f2', '#991b1b']
    };

    const [background, color] = colors[type] || colors.info;

    element.style.display = 'block';
    element.style.backgroundColor = background;
    element.style.color = color;
    element.textContent = message;
  }

  async loadApplicationDocuments() {
    const applicationId = this.getApplicationId();
    const tbody = this.container.querySelector(
      '#preflight-document-rows'
    );

    if (!applicationId) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5">
            No application is selected. Select an application
            before uploading documents.
          </td>
        </tr>
      `;

      this.container.querySelector(
        '#preflight-doc-count'
      ).textContent = 'No application selected';

      return;
    }

    try {
      const response = await api.getApplication(applicationId);

      this.application = response.data;

      store.setState({
        activeApplicationData: this.application
      });

      this.renderDocumentRows();
    } catch (error) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5">
            Unable to load documents:
            ${escapeHtml(error.message)}
          </td>
        </tr>
      `;

      this.container.querySelector(
        '#preflight-doc-count'
      ).textContent = 'Load failed';

      this.showMessage(
        `Could not load the selected application. ${error.message}`,
        'error'
      );
    }
  }

  getLatestDocument(documentType) {
    const documents = this.application?.documents || [];

    const matchingDocuments = documents.filter((doc) =>
      (doc.document_type || doc.documentType) === documentType
    );

    return matchingDocuments.length
      ? matchingDocuments[matchingDocuments.length - 1]
      : null;
  }

  renderDocumentRows() {
    const tbody = this.container.querySelector(
      '#preflight-document-rows'
    );

    const documents = this.application?.documents || [];

    this.container.querySelector(
      '#preflight-doc-count'
    ).textContent =
      `${documents.length} uploaded document${documents.length === 1 ? '' : 's'}`;

    tbody.innerHTML = DOCUMENT_TYPES.map((item, index) => {
      const doc = this.getLatestDocument(item.type);
      const filename =
        doc?.original_filename || doc?.filename || '';

      const status = doc?.verification_status || 'Not uploaded';
      const size = formatFileSize(doc?.file_size_bytes);
      const badgeClass = doc ? 'badge' : 'badge-expired';

      return `
        <tr>
          <td>
            <strong>${escapeHtml(item.name)}</strong>
          </td>

          <td>${escapeHtml(item.format)}</td>

          <td>
            ${
              doc
                ? `${escapeHtml(filename)}${size ? ` (${escapeHtml(size)})` : ''}`
                : 'No file uploaded'
            }
          </td>

          <td>
            <span class="${badgeClass}">
              ${escapeHtml(String(status).toUpperCase())}
            </span>
          </td>

          <td>
            <input
              type="file"
              id="preflight-file-${index}"
              accept=".pdf,.jpg,.jpeg,.png"
              hidden
            />

            <button
              type="button"
              class="btn btn-outline btn-sm"
              data-upload-index="${index}"
              ${this.uploadingTypes.has(item.type) ? 'disabled' : ''}
            >
              ${
                this.uploadingTypes.has(item.type)
                  ? 'Uploading...'
                  : doc
                    ? 'Replace'
                    : 'Upload'
              }
            </button>
          </td>
        </tr>
      `;
    }).join('');

    DOCUMENT_TYPES.forEach((item, index) => {
      const input = this.container.querySelector(
        `#preflight-file-${index}`
      );

      const button = this.container.querySelector(
        `[data-upload-index="${index}"]`
      );

      button.addEventListener('click', () => input.click());

      input.addEventListener('change', async () => {
        const file = input.files?.[0];

        if (!file) return;

        await this.uploadDocument(item, file);

        input.value = '';
      });
    });
  }

  async uploadDocument(item, file) {
    const applicationId = this.getApplicationId();

    if (!applicationId) {
      this.showMessage(
        'Select an application before uploading a document.',
        'error'
      );
      return;
    }

    const allowedTypes = [
      'application/pdf',
      'image/jpeg',
      'image/png'
    ];

    const allowedExtensions = /\.(pdf|jpe?g|png)$/i;

    if (!allowedExtensions.test(file.name)) {
      this.showMessage(
        'Choose a PDF, JPG, or PNG file.',
        'error'
      );
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      this.showMessage(
        'The file must be 25 MB or smaller.',
        'error'
      );
      return;
    }

    if (file.type && !allowedTypes.includes(file.type)) {
      this.showMessage(
        'The selected file must be a PDF, JPEG, or PNG.',
        'error'
      );
      return;
    }

    this.uploadingTypes.add(item.type);
    this.renderDocumentRows();

    this.showMessage(`Uploading ${file.name}...`, 'info');

    try {
      await api.uploadDocument(file, item.type, applicationId);

      this.showMessage(
        `${file.name} was uploaded successfully. Refreshing the document list...`,
        'success'
      );

      // The backend appends uploaded documents.
      // It does not automatically delete previous versions.
      await this.loadApplicationDocuments();
    } catch (error) {
      this.showMessage(
        `Upload failed: ${error.message}`,
        'error'
      );
    } finally {
      this.uploadingTypes.delete(item.type);
      this.renderDocumentRows();
    }
  }

  renderReviewResults(report) {
    const banner = this.container.querySelector(
      '#preflight-results-banner'
    );

    const summary = report?.summary || {};

    const tasks = Array.isArray(report?.unresolved_tasks)
      ? report.unresolved_tasks
      : [];

    const cards = [
      ['Checks Planned', summary.total_planned],
      ['Checks Executed', summary.total_executed],
      ['Compliant', summary.compliant],
      ['Deficiencies', summary.deficiencies],
      ['Anomalies', summary.anomalies],
      ['Not Applicable', summary.not_applicable],
      ['Inconclusive', summary.inconclusive],
      ['Source Verifications', summary.source_verifications],
      ['Unresolved Tasks', summary.unresolved_tasks]
    ];

    banner.style.display = 'block';
    banner.style.backgroundColor = '#f8fafc';
    banner.style.border = '1px solid #cbd5e1';
    banner.style.color = '#0f172a';

    const cardHtml = cards.map(([label, value]) => `
      <div style="
        background:#ffffff;
        border:1px solid #e2e8f0;
        border-radius:8px;
        padding:14px;
        min-width:0
      ">
        <div style="
          font-size:12px;
          color:#64748b;
          margin-bottom:8px
        ">
          ${escapeHtml(label)}
        </div>

        <div style="
          font-size:24px;
          font-weight:700;
          overflow-wrap:anywhere
        ">
          ${escapeHtml(value ?? 'N/A')}
        </div>
      </div>
    `).join('');

    const taskHtml = tasks.length
      ? `
        <ul style="margin:0;padding-left:22px">
          ${tasks.map((task) => {
            const text = typeof task === 'string'
              ? task
              : JSON.stringify(task);

            return `
              <li style="margin-bottom:10px;line-height:1.6">
                ${escapeHtml(text)}
              </li>
            `;
          }).join('')}
        </ul>
      `
      : '<p>No unresolved tasks were returned by the backend.</p>';

    const formattedReport = escapeHtml(
      JSON.stringify(report, null, 2)
    );

    banner.innerHTML = `
      <h2 style="
        margin:0 0 8px;
        font-size:20px;
        color:#0f172a
      ">
        Pre-Flight Diagnostic Results
      </h2>

      <p style="
        margin:0 0 18px;
        font-size:13px;
        line-height:1.6;
        color:#475569
      ">
        Results returned by the PRAMAAN-AI backend.
        Review unresolved items before proceeding.
      </p>

      <div style="
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(135px,1fr));
        gap:12px;
        margin-bottom:22px
      ">
        ${cardHtml}
      </div>

      <section style="margin-bottom:18px">
        <h3 style="margin:0 0 10px;font-size:16px">
          Items Requiring Attention
        </h3>

        ${taskHtml}
      </section>

      <details style="
        border:1px solid #e2e8f0;
        border-radius:8px;
        padding:12px;
        background:#ffffff
      ">
        <summary style="
          cursor:pointer;
          font-weight:600;
          font-size:13px
        ">
          View Complete Backend Report
        </summary>

        <pre style="
          margin-top:12px;
          white-space:pre-wrap;
          overflow-wrap:anywhere;
          max-height:420px;
          overflow:auto;
          font-size:12px;
          line-height:1.5;
          color:#334155
        ">${formattedReport}</pre>
      </details>

      <p style="
        margin:14px 0 0;
        font-size:11px;
        color:#64748b;
        line-height:1.5
      ">
        This is a prototype decision-support result.
        It does not represent official AICTE approval.
      </p>
    `;
  }

  async runPreflight() {
    const applicationId = this.getApplicationId();

    const button = this.container.querySelector(
      '#btn-run-preflight'
    );

    const banner = this.container.querySelector(
      '#preflight-results-banner'
    );

    if (!applicationId) {
      this.showMessage(
        'Select an application before running the diagnostic.',
        'error'
      );
      return;
    }

    button.disabled = true;
    button.textContent = 'Running checks...';
    banner.style.display = 'none';

    this.showMessage(
      'Sending the selected application for a full backend review...',
      'info'
    );

    try {
      const response = await api.runFullReview(applicationId);
      const report = response.data;

      this.renderReviewResults(report);

      this.showMessage(
        'The full-review request completed successfully.',
        'success'
      );
    } catch (error) {
      banner.style.display = 'block';
      banner.style.backgroundColor = '#fef2f2';
      banner.style.border = '1px solid #fecaca';
      banner.style.color = '#991b1b';

      banner.textContent =
        `The backend review failed: ${error.message}`;

      this.showMessage(
        `Review failed: ${error.message}`,
        'error'
      );
    } finally {
      button.disabled = false;
      button.textContent = 'Run Pre-Flight Diagnostic';
    }
  }
}
