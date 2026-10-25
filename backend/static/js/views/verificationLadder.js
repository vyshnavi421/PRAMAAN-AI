/**
 * PRAMAAN-AI Verification Ladder View Controller
 * External Issuing Authority & Cryptographic Verification Adapters.
 * Strictly supports the 6 exact statutory document-verification statuses:
 * - verified
 * - mismatch detected
 * - expired
 * - verification pending
 * - source unavailable
 * - manual review required
 *
 * Implements truthfulness guardrails, honest uncertainty, bounded retries (cap 3),
 * response hashing, and audit ledger traceability.
 */
import { api } from '../api.js';
import { esc } from '../util.js';
import { store } from '../state.js';

export class VerificationLadderView {
  constructor(container) {
    this.container = container;
    this.adapters = [];
    this.fixtures = {};
    this.applications = [];
    this.selectedDocId = 'doc-clean-fire';
    this.selectedAdapterId = 'SIMULATED_ISSUER_REGISTRY_ADAPTER';
    this.selectedMethod = 'ISSUER_REGISTRY';
    this.selectedFixture = 'FIX-VERIFIED';
    this.lastAttempt = null;
    this.attemptsHistory = [];
  }

  getBadgeClass(status) {
    const s = String(status || '').toLowerCase();
    if (s === 'verified') return 'badge-verified';
    if (s === 'mismatch detected' || s.includes('mismatch')) return 'badge-mismatch';
    if (s === 'expired') return 'badge-expired';
    if (s === 'verification pending' || s.includes('pending')) return 'badge-pending';
    if (s === 'source unavailable' || s.includes('unavail')) return 'badge-source-unavailable';
    return 'badge-manual-review';
  }

  async render() {
    this.container.innerHTML = `
      <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
        <!-- Header -->
        <div class="page-header" style="margin-bottom: 20px;">
          <div>
            <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--cobalt-600); margin-bottom: 2px;">
              Verification Subsystem · Statutory Adapters
            </div>
            <h1 class="page-title">External Issuing Authority & Cryptographic Verification</h1>
            <p class="page-desc">Deterministic statutory registry lookups, PKCS#7 signatures, and 2D QR decoding supporting the 6 statutory verification states</p>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <span class="badge" style="background: var(--navy-900); color: var(--navy-100); font-family: var(--font-mono); font-size: 11px;">
              DEMO / SIMULATED MODE
            </span>
            <button id="btn-refresh-adapters" class="btn btn-outline btn-sm">Refresh Adapters</button>
          </div>
        </div>

        <!-- Statutory Guardrail Banner -->
        <div style="background-color: var(--status-source-unavail-bg); border: 1px solid var(--status-source-unavail-border); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 24px; display: flex; align-items: flex-start; gap: 14px;">
          <svg width="22" height="22" fill="var(--status-source-unavail-fg)" viewBox="0 0 20 20" style="flex-shrink: 0; margin-top: 2px;">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
          </svg>
          <div style="font-size: 13px; color: var(--status-source-unavail-fg); line-height: 1.5;">
            <strong>Statutory Truthfulness Guardrail:</strong> An external issuer portal timeout, offline endpoint, or unreachable registry is classified strictly as <strong>source unavailable</strong> with bounded retries (cap: 3) and automatically dispatched to manual review. External network conditions <strong>never penalize the applicant institution</strong> or produce false fraud accusations.
          </div>
        </div>

        <!-- Grid Layout: Adapters Table on Top, Interactive Sandbox & History below -->
        <div style="display: grid; grid-template-columns: 1fr; gap: 24px;">
          
          <!-- Section 1: Active Adapters Catalog -->
          <div class="table-card">
            <div class="table-toolbar" style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-weight: 700; font-size: 15px; color: var(--navy-950);">Active Verification Adapters</span>
                <div style="font-size: 11px; color: var(--slate-500);">Provider-agnostic interfaces returning exact statutory verification responses</div>
              </div>
              <span class="badge badge-verified">6 STATUTORY LABELS ENFORCED</span>
            </div>
            <div style="overflow-x: auto;">
              <table class="data-table" id="adapters-table">
                <thead>
                  <tr>
                    <th>Adapter Name & ID</th>
                    <th>Supported Verification Methods</th>
                    <th>Covered Document Types</th>
                    <th>Operational State</th>
                    <th>Simulation Mode</th>
                    <th>Admin Action</th>
                  </tr>
                </thead>
                <tbody id="adapters-tbody">
                  <tr><td colspan="6" style="text-align: center; color: var(--slate-500); padding: 20px;">Loading verification adapters...</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Section 2: Interactive Verification Sandbox -->
          <div style="display: grid; grid-template-columns: 1.1fr 1fr; gap: 24px;">
            
            <!-- Left: Execution Controls Card -->
            <div class="table-card" style="padding: 20px;">
              <div style="border-bottom: 1px solid var(--slate-200); padding-bottom: 12px; margin-bottom: 16px;">
                <h3 style="font-size: 15px; font-weight: 700; color: var(--navy-950); margin: 0 0 4px 0;">Interactive Verification Sandbox</h3>
                <p style="font-size: 12px; color: var(--slate-500); margin: 0;">Trigger live verification requests, simulate outages, test bounded retries, and inspect safe evidence hashes.</p>
              </div>

              <div style="display: flex; flex-direction: column; gap: 14px;">
                <div>
                  <label style="font-size: 12px; font-weight: 600; color: var(--slate-700); display: block; margin-bottom: 4px;">Target Dossier Document</label>
                  <select id="select-document" class="form-control" style="width: 100%; font-size: 12px;">
                    <option value="doc-clean-fire">Apex Tech - Fire Safety NOC (doc-clean-fire)</option>
                    <option value="doc-clean-affidavit">Apex Tech - General Affidavit (doc-clean-affidavit)</option>
                    <option value="doc-expired-fire">National Academy - Fire Safety NOC [Expired Seed] (doc-expired-fire)</option>
                    <option value="doc-mismatch-land">City College - Land Use Certificate [Discrepant Area] (doc-mismatch-land)</option>
                    <option value="doc-unavail-fire">Suburban Institute - Fire NOC [504 Timeout] (doc-unavail-fire)</option>
                  </select>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                  <div>
                    <label style="font-size: 12px; font-weight: 600; color: var(--slate-700); display: block; margin-bottom: 4px;">Verification Method</label>
                    <select id="select-method" class="form-control" style="width: 100%; font-size: 12px;">
                      <option value="ISSUER_REGISTRY">ISSUER_REGISTRY (Authority Portal)</option>
                      <option value="DIGITAL_SIGNATURE">DIGITAL_SIGNATURE (PKCS#7 / X.509)</option>
                      <option value="QR_CODE">QR_CODE (2D Encrypted Symbol)</option>
                    </select>
                  </div>

                  <div>
                    <label style="font-size: 12px; font-weight: 600; color: var(--slate-700); display: block; margin-bottom: 4px;">Select Verification Adapter</label>
                    <select id="select-adapter" class="form-control" style="width: 100%; font-size: 12px;">
                      <option value="SIMULATED_ISSUER_REGISTRY_ADAPTER">Simulated Government Issuer Registry</option>
                      <option value="SIMULATED_PKI_SIGNATURE_ADAPTER">Simulated PKCS#7 / X.509 Validator</option>
                      <option value="SIMULATED_2D_QR_ADAPTER">Simulated 2D Barcode & QR Decrypter</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label style="font-size: 12px; font-weight: 600; color: var(--slate-700); display: block; margin-bottom: 4px;">Deterministic Scenario / Fixture</label>
                  <select id="select-fixture" class="form-control" style="width: 100%; font-size: 12px;">
                    <option value="FIX-VERIFIED">FIX-VERIFIED → verified (Active clearance matches claims)</option>
                    <option value="FIX-MISMATCH">FIX-MISMATCH → mismatch detected (Discrepant registered area)</option>
                    <option value="FIX-EXPIRED">FIX-EXPIRED → expired (Clearance validity lapsed on issuer portal)</option>
                    <option value="FIX-PENDING">FIX-PENDING → verification pending (Clearance currently processing)</option>
                    <option value="FIX-SOURCE-UNAVAIL">FIX-SOURCE-UNAVAIL → source unavailable (504 Gateway Timeout)</option>
                    <option value="FIX-MANUAL-REVIEW">FIX-MANUAL-REVIEW → manual review required (Ambiguous boundary records)</option>
                    <option value="ERR-TIMEOUT">ERR-TIMEOUT → source unavailable (Transient timeout with 3-retry cap)</option>
                    <option value="ERR-MALFORMED">ERR-MALFORMED → manual review required (Corrupt/unparseable HTML payload)</option>
                    <option value="SIG-VALID">SIG-VALID → verified (Valid PKI signature & certificate chain)</option>
                    <option value="SIG-MISMATCH-TAMPER">SIG-MISMATCH-TAMPER → mismatch detected (Post-signing byte modification)</option>
                    <option value="SIG-EXPIRED">SIG-EXPIRED → expired (Signing certificate was expired at signing time)</option>
                    <option value="SIG-TIMEOUT">SIG-TIMEOUT → source unavailable (OCSP revocation server timeout)</option>
                    <option value="QR-VALID">QR-VALID → verified (Encrypted HMAC payload decrypted)</option>
                    <option value="QR-MISMATCH">QR-MISMATCH → mismatch detected (Embedded intake differs from document)</option>
                    <option value="QR-MANUAL-DAMAGE">QR-MANUAL-DAMAGE → manual review required (Reed-Solomon ECC failure)</option>
                  </select>
                </div>

                <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: #f8fafc; border-radius: 6px; border: 1px solid var(--slate-200);">
                  <div style="font-size: 12px; color: var(--slate-700);">
                    <strong>Simulate Retry on Transient Error:</strong>
                    <div style="font-size: 11px; color: var(--slate-500);">Applies bounded retry backoff (max 3 attempts).</div>
                  </div>
                  <input type="checkbox" id="chk-simulate-retry" checked style="width: 16px; height: 16px;">
                </div>

                <div style="display: flex; gap: 10px; margin-top: 6px;">
                  <button id="btn-execute-verify" class="btn btn-primary" style="flex: 1;">
                    Execute Statutory Verification
                  </button>
                </div>
              </div>
            </div>

            <!-- Right: Real-Time Execution Result Card -->
            <div class="table-card" style="padding: 20px; display: flex; flex-direction: column;">
              <div style="border-bottom: 1px solid var(--slate-200); padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
                <h3 style="font-size: 15px; font-weight: 700; color: var(--navy-950); margin: 0;">Live Verification Outcome</h3>
                <span id="result-status-badge" class="badge badge-pending">PENDING EXECUTION</span>
              </div>

              <div id="result-empty-state" style="padding: 40px 20px; text-align: center; color: var(--slate-400); font-size: 13px;">
                Select a document and fixture on the left, then click <strong>Execute Statutory Verification</strong> to inspect the live response.
              </div>

              <div id="result-content" style="display: none; flex-direction: column; gap: 12px;">
                <!-- Mechanism Performed -->
                <div style="padding: 10px 14px; background: #f8fafc; border-radius: 6px; border-left: 3px solid var(--cobalt-600);">
                  <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: var(--slate-500);">Mechanism Performed</div>
                  <div id="res-mechanism" style="font-size: 12px; font-weight: 600; color: var(--navy-950); margin-top: 2px;">-</div>
                </div>

                <!-- Scope Limitations -->
                <div style="padding: 10px 14px; background: #fffbeb; border: 1px solid #fef3c7; border-radius: 6px;">
                  <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #b45309;">Scope & Evidentiary Limitations</div>
                  <div id="res-limitations" style="font-size: 12px; color: #92400e; margin-top: 2px; line-height: 1.4;">-</div>
                </div>

                <!-- Response Hash & Retry Info -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                  <div style="padding: 8px 12px; background: #f1f5f9; border-radius: 6px;">
                    <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: var(--slate-500);">Safe Response Hash</div>
                    <div id="res-hash" class="mono-hash" style="font-size: 11px; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">-</div>
                  </div>
                  <div style="padding: 8px 12px; background: #f1f5f9; border-radius: 6px;">
                    <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: var(--slate-500);">Retry Outcome</div>
                    <div id="res-retry" style="font-size: 11px; font-weight: 600; color: var(--slate-700); margin-top: 2px;">-</div>
                  </div>
                </div>

                <!-- Manual Review Task if applicable -->
                <div id="res-task-container" style="display: none; padding: 10px 14px; background: var(--status-source-unavail-bg); border: 1px solid var(--status-source-unavail-border); border-radius: 6px;">
                  <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: var(--status-source-unavail-fg);">Statutory Review Task Created</div>
                  <div id="res-task" style="font-size: 12px; color: var(--status-source-unavail-fg); margin-top: 2px; font-weight: 600;">-</div>
                </div>

                <!-- Inspect Raw JSON toggle -->
                <div style="margin-top: 6px;">
                  <button id="btn-toggle-raw" class="btn btn-outline btn-sm" style="width: 100%;">
                    Inspect Raw Adapter Payload JSON ▾
                  </button>
                  <pre id="raw-payload-pre" style="display: none; margin-top: 8px; background: var(--navy-950); color: #38bdf8; padding: 12px; border-radius: 6px; font-family: var(--font-mono); font-size: 11px; max-height: 200px; overflow-y: auto;"></pre>
                </div>
              </div>
            </div>

          </div>

          <!-- Section 3: Chronological Document Attempt History -->
          <div class="table-card">
            <div class="table-toolbar">
              <div>
                <span style="font-weight: 700; font-size: 14px; color: var(--navy-950);">Document Verification Attempt Ledger</span>
                <div style="font-size: 11px; color: var(--slate-500);">Timestamped cryptographic attempts linked to immutable audit trail</div>
              </div>
              <span id="history-count-badge" class="badge" style="background: var(--slate-100); color: var(--slate-700);">0 ATTEMPTS</span>
            </div>
            <div style="overflow-x: auto;">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Attempt ID</th>
                    <th>Document Reference</th>
                    <th>Method</th>
                    <th>Adapter</th>
                    <th>Statutory Status</th>
                    <th>Retry Count</th>
                    <th>SHA-256 Hash</th>
                    <th>Timestamp (UTC)</th>
                  </tr>
                </thead>
                <tbody id="history-tbody">
                  <tr><td colspan="8" style="text-align: center; color: var(--slate-500); padding: 16px;">No attempts recorded for this document yet.</td></tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    `;

    await this.loadAdapters();
    await this.loadActiveApplicationDocuments();
    this.wireEvents();
    await this.refreshHistory();
  }

  async loadActiveApplicationDocuments() {
    const select = document.getElementById('select-document');
    const app = store.getState().activeApplicationData;
    if (!select || !app || !Array.isArray(app.documents) || app.documents.length === 0) return;

    const existing = new Set(Array.from(select.options, (option) => option.value));
    app.documents.forEach((doc) => {
      if (existing.has(doc.id)) return;
      const option = document.createElement('option');
      const suffix = String(doc.id || '').slice(0, 8);
      option.value = doc.id;
      option.textContent = `Current dossier · ${doc.document_type} — ${doc.original_filename} (${suffix})`;
      select.append(option);
    });

    // Prefer an actual uploaded file in the active dossier, then its Fire Safety NOC,
    // so the verification demo can follow the same document from intake to issuer check.
    const documents = app.documents.slice();
    const preferred = documents.slice().reverse().find(
      (doc) => String(doc.storage_key || '').startsWith('storage/protected/')
    ) || documents.find((doc) => doc.document_type === 'FIRE_SAFETY_NOC') || documents[0];

    if (preferred && existing.has(preferred.id) === false) {
      select.value = preferred.id;
      this.selectedDocId = preferred.id;
    } else if (preferred && Array.from(select.options).some((option) => option.value === preferred.id)) {
      select.value = preferred.id;
      this.selectedDocId = preferred.id;
    }
  }

  async loadAdapters() {
    try {
      const res = await api.listVerificationAdapters();
      this.adapters = res.data.adapters || [];
      this.renderAdaptersTable();
    } catch (err) {
      console.error('Failed to load adapters:', err);
      const tbody = document.getElementById('adapters-tbody');
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" style="color: var(--severity-deficiency-fg); padding: 16px;">Failed to load adapters: ${esc(err.message)}</td></tr>`;
      }
    }
  }

  renderAdaptersTable() {
    const tbody = document.getElementById('adapters-tbody');
    if (!tbody) return;

    if (!this.adapters || this.adapters.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--slate-500); padding: 16px;">No adapters registered.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.adapters.map(a => {
      const methodsHtml = a.supported_methods.map(m => `<span class="badge" style="background: #e0e7ff; color: #3730a3; margin-right: 4px; font-size: 10px;">${m}</span>`).join('');
      const statusBadge = a.is_enabled
        ? `<span class="badge badge-verified">OPERATIONAL</span>`
        : `<span class="badge badge-source-unavailable">DISABLED (OUTAGE)</span>`;
      const toggleActionLabel = a.is_enabled ? 'Simulate Outage' : 'Restore Online';
      const toggleClass = a.is_enabled ? 'btn-outline' : 'btn-primary';

      return `
        <tr>
          <td>
            <strong>${esc(a.adapter_name)}</strong>
            <div class="mono-hash" style="font-size: 10px; color: var(--slate-500);">${esc(a.adapter_id)}</div>
          </td>
          <td>${methodsHtml}</td>
          <td><span style="font-size: 11px; color: var(--slate-600);">${esc(a.supported_document_types.length)} Document Categories</span></td>
          <td>${statusBadge}</td>
          <td><span style="font-size: 11px; font-weight: 600; color: var(--cobalt-600);">SYNTHETIC DEMO</span></td>
          <td>
            <button class="btn ${toggleClass} btn-sm" onclick="window.appRouter.views.verification.toggleAdapter('${esc(a.adapter_id)}', ${!a.is_enabled})">
              ${toggleActionLabel}
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  async toggleAdapter(adapterId, targetState) {
    try {
      await api.toggleVerificationAdapter(adapterId, targetState);
      window.appToast.show(`Adapter ${adapterId} ${targetState ? 'enabled' : 'disabled'}.`);
      await this.loadAdapters();
    } catch (err) {
      window.appToast.show(`Failed to toggle adapter: ${err.message}`);
    }
  }

  wireEvents() {
    const docSelect = document.getElementById('select-document');
    const methodSelect = document.getElementById('select-method');
    const adapterSelect = document.getElementById('select-adapter');
    const fixtureSelect = document.getElementById('select-fixture');
    const btnExecute = document.getElementById('btn-execute-verify');
    const btnRefresh = document.getElementById('btn-refresh-adapters');
    const btnToggleRaw = document.getElementById('btn-toggle-raw');

    if (docSelect) {
      docSelect.onchange = (e) => {
        this.selectedDocId = e.target.value;
        this.refreshHistory();
      };
    }

    if (methodSelect) {
      methodSelect.onchange = (e) => {
        this.selectedMethod = e.target.value;
        if (this.selectedMethod === 'DIGITAL_SIGNATURE') {
          adapterSelect.value = 'SIMULATED_PKI_SIGNATURE_ADAPTER';
          fixtureSelect.value = 'SIG-VALID';
        } else if (this.selectedMethod === 'QR_CODE') {
          adapterSelect.value = 'SIMULATED_2D_QR_ADAPTER';
          fixtureSelect.value = 'QR-VALID';
        } else {
          adapterSelect.value = 'SIMULATED_ISSUER_REGISTRY_ADAPTER';
          fixtureSelect.value = 'FIX-VERIFIED';
        }
      };
    }

    if (btnExecute) {
      btnExecute.onclick = () => this.executeVerification();
    }

    if (btnRefresh) {
      btnRefresh.onclick = () => {
        this.loadAdapters();
        this.refreshHistory();
        window.appToast.show('Adapters and history refreshed.');
      };
    }

    if (btnToggleRaw) {
      btnToggleRaw.onclick = () => {
        const pre = document.getElementById('raw-payload-pre');
        if (pre) {
          const isShown = pre.style.display === 'block';
          pre.style.display = isShown ? 'none' : 'block';
          btnToggleRaw.textContent = isShown
            ? 'Inspect Raw Adapter Payload JSON ▾'
            : 'Hide Raw Adapter Payload JSON ▴';
        }
      };
    }
  }

  async executeVerification() {
    const docId = document.getElementById('select-document').value;
    const adapterId = document.getElementById('select-adapter').value;
    const method = document.getElementById('select-method').value;
    const fixture = document.getElementById('select-fixture').value;
    const simulateRetry = document.getElementById('chk-simulate-retry').checked;
    const btn = document.getElementById('btn-execute-verify');

    btn.disabled = true;
    btn.textContent = 'Verifying with Adapter...';

    try {
      const res = await api.verifyDocument(docId, {
        adapter_id: adapterId,
        method: method,
        reference_id: fixture,
        max_retries: 3,
        simulate_retry: simulateRetry,
        actor_id: 'usr-officer-01'
      });

      this.lastAttempt = res.data;
      this.displayOutcome(this.lastAttempt);
      await this.refreshHistory();
      window.appToast.show(`Statutory status: ${this.lastAttempt.status.toUpperCase()}`);
    } catch (err) {
      window.appToast.show(`Verification call failed: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Execute Statutory Verification';
    }
  }

  displayOutcome(attempt) {
    const emptyState = document.getElementById('result-empty-state');
    const resultContent = document.getElementById('result-content');
    const badge = document.getElementById('result-status-badge');
    const mechanism = document.getElementById('res-mechanism');
    const limitations = document.getElementById('res-limitations');
    const hashEl = document.getElementById('res-hash');
    const retryEl = document.getElementById('res-retry');
    const taskContainer = document.getElementById('res-task-container');
    const taskEl = document.getElementById('res-task');
    const rawPre = document.getElementById('raw-payload-pre');

    if (!emptyState || !resultContent) return;

    emptyState.style.display = 'none';
    resultContent.style.display = 'flex';

    badge.className = `badge ${this.getBadgeClass(attempt.status)}`;
    badge.textContent = attempt.status.toUpperCase();

    mechanism.textContent = attempt.mechanism_performed || 'Verification check executed.';
    limitations.textContent = attempt.scope_limitations || 'Standard statutory verification.';
    hashEl.textContent = attempt.response_hash || 'None';
    hashEl.title = attempt.response_hash || '';

    const retryText = attempt.retry_count > 0
      ? `${attempt.retry_count} retries (${attempt.retry_outcome})`
      : `${attempt.retry_outcome || 'First attempt (0 retries)'}`;
    retryEl.textContent = retryText;

    if (attempt.manual_review_task) {
      taskContainer.style.display = 'block';
      taskEl.textContent = attempt.manual_review_task;
    } else {
      taskContainer.style.display = 'none';
    }

    if (rawPre) {
      rawPre.textContent = JSON.stringify(attempt.response_payload, null, 2);
    }
  }

  async refreshHistory() {
    try {
      const res = await api.getDocumentVerificationAttempts(this.selectedDocId);
      this.attemptsHistory = res.data || [];
      this.renderHistoryTable();
    } catch (err) {
      console.warn('History fetch error:', err);
    }
  }

  renderHistoryTable() {
    const tbody = document.getElementById('history-tbody');
    const countBadge = document.getElementById('history-count-badge');
    if (!tbody) return;

    if (countBadge) {
      countBadge.textContent = `${this.attemptsHistory.length} ATTEMPTS`;
    }

    if (!this.attemptsHistory || this.attemptsHistory.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--slate-500); padding: 16px;">No attempts recorded for ${this.selectedDocId} yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.attemptsHistory.slice().reverse().map(att => {
      const dateStr = new Date(att.attempted_at).toLocaleTimeString();
      return `
        <tr>
          <td><span class="mono-hash" style="font-size: 10px;">${att.id.slice(0, 8)}</span></td>
          <td><strong>${esc(att.request_reference)}</strong></td>
          <td><span class="badge" style="background: #e0e7ff; color: #3730a3; font-size: 10px;">${esc(att.verification_method)}</span></td>
          <td style="font-size: 11px;">${esc(att.adapter_name)}</td>
          <td><span class="badge ${this.getBadgeClass(att.status)}">${esc(att.status)}</span></td>
          <td style="font-size: 11px; text-align: center;">${esc(att.retry_count)}</td>
          <td><span class="mono-hash" style="font-size: 10px;" title="${esc(att.response_hash || '')}">${(att.response_hash || '').slice(0, 12)}...</span></td>
          <td style="font-size: 11px; color: var(--slate-500);">${dateStr}</td>
        </tr>
      `;
    }).join('');
  }
}
