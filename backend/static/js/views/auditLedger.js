/**
 * PRAMAAN-AI Cryptographic Hash-Chained Audit Ledger View Controller
 * Features:
 * 1. Sequential mathematical hash chain verification: H_i = SHA256(H_{i-1} || timestamp || actor || type || payload)
 * 2. Disposable audit tampering test: Deliberately alters an in-memory event to verify instant tamper exposure
 * 3. 1-click restore to original signed state
 * 4. Plain-language statutory disclosure on the mathematical boundaries of hash chaining
 */
import { api } from '../api.js';
import { esc } from '../util.js';
import { store } from '../state.js';

export class AuditLedgerView {
  constructor(container) {
    this.container = container;
  }

  async render() {
    this.container.innerHTML = `
      <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
        <!-- Header -->
        <div class="page-header" style="margin-bottom: 20px;">
          <div>
            <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--cobalt-600); margin-bottom: 2px;">
              Tamper-Evident Governance · Audit Subsystem
            </div>
            <h1 class="page-title">Cryptographic Hash-Chained Audit Ledger</h1>
            <p class="page-desc">Every rule applied, verification attempted, document accessed, and reviewer action is immutably chained via SHA-256</p>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button id="btn-verify-chain-now" class="btn btn-primary btn-sm">
              ⚡ Verify Hash Chain
            </button>
            <button id="btn-simulate-tamper" class="btn btn-outline btn-sm" style="color: var(--status-source-unavail-fg); border-color: var(--status-source-unavail-border);">
              ⚠️ Simulate Disposable Tamper
            </button>
            <button id="btn-restore-chain" class="btn btn-outline btn-sm" style="display: none;">
              🔄 Restore Chain
            </button>
          </div>
        </div>

        <!-- Verification Status Banner -->
        <div id="chain-status-banner" style="background-color: var(--status-verified-bg); border: 1px solid var(--status-verified-border); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span class="health-dot"></span>
            <div>
              <span id="chain-status-text" style="font-size: 13px; font-weight: 700; color: var(--status-verified-fg);">
                Cryptographic Audit Chain Intact • Ready for Verification
              </span>
              <div id="chain-detail-text" style="font-size: 11px; color: var(--slate-600); margin-top: 2px;">
                Sequential verification from Genesis block (000000...) to Head block.
              </div>
            </div>
          </div>
          <span id="chain-evaluated-count" class="mono-hash" style="font-size: 11px; padding: 4px 8px; background: white; border-radius: 4px; border: 1px solid var(--slate-200);">
            Ready
          </span>
        </div>

        <!-- Mathematical Limitation Notice Banner -->
        <div style="background-color: #f8fafc; border: 1px solid var(--slate-200); border-left: 4px solid var(--cobalt-600); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 24px;">
          <div style="font-size: 11px; font-weight: 700; color: var(--navy-950); text-transform: uppercase; margin-bottom: 4px;">
            Statutory Cryptographic Ledger Limitation Notice (docs/THREAT_MODEL.md §3)
          </div>
          <div style="font-size: 12px; color: var(--slate-700); line-height: 1.5;">
            Cryptographic hash chaining within the application database reliably exposes unauthorized modifications, deletions,
            or localized updates by application users, compromised API accounts, or SQL injection. 
            However, it does <strong>not</strong> provide absolute immutability against a database superuser who could maliciously rewrite
            the entire database table and recompute all hashes sequentially from the corrupted point forward.
            For production deployment, periodic checkpoint hashes must be anchored to Write-Once-Read-Many (WORM) storage or a public timestamping notary.
          </div>
        </div>

        <!-- Audit Event Log Table -->
        <div class="table-card">
          <div class="table-toolbar" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span style="font-weight: 700; font-size: 14px; color: var(--navy-950);">Immutable Audit Trail Records</span>
              <div style="font-size: 11px; color: var(--slate-500);">Append-only log verifying that scrutiny decisions and document access cannot be secretly altered</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-outline btn-sm" onclick="window.appRouter.views.audit.loadEvents()">Refresh Ledger</button>
            </div>
          </div>
          <div id="audit-table-body" style="overflow-x: auto;">
            <div style="padding: 24px; text-align: center; color: var(--slate-500);">Loading audit ledger from backend...</div>
          </div>
        </div>
      </div>
    `;

    document.getElementById('btn-verify-chain-now').onclick = () => this.verifyChain();
    document.getElementById('btn-simulate-tamper').onclick = () => this.simulateTamper();
    document.getElementById('btn-restore-chain').onclick = () => this.restoreChain();
    await this.loadEvents();
  }

  async loadEvents() {
    const s = store.getState();
    try {
      const res = await api.getAuditEvents(s.activeApplicationId);
      const events = res.data || [];

      if (events.length === 0) {
        document.getElementById('audit-table-body').innerHTML = `
          <div style="padding: 32px; text-align: center; color: var(--slate-500);">No audit events recorded for this application yet.</div>
        `;
        return;
      }

      let rows = '';
      for (const evt of events) {
        const isTampered = evt.details && evt.details.UNAUTHORIZED_MUTATION;
        const rowClass = isTampered ? 'style="background: #fff1f2;"' : '';
        const badgeClass = isTampered ? 'badge-deficiency' : 'badge-compliant';
        const displayType = isTampered ? `${esc(evt.event_type)} [TAMPERED]` : evt.event_type;

        rows += `
          <tr ${rowClass}>
            <td><strong>#${evt.sequence}</strong></td>
            <td><span class="mono-hash" style="font-size: 10px;">${evt.timestamp.slice(0, 19).replace('T', ' ')}</span></td>
            <td><strong style="font-size: 11px;">${esc(evt.actor_id)}</strong></td>
            <td><span class="badge ${badgeClass}" style="font-size: 10px;">${displayType}</span></td>
            <td><span class="mono-hash" style="font-size: 10px;" title="${esc(evt.event_hash)}">${evt.event_hash.slice(0, 14)}...</span></td>
            <td><span class="mono-hash" style="font-size: 10px;" title="${esc(evt.previous_hash)}">${evt.previous_hash.slice(0, 14)}...</span></td>
          </tr>
        `;
      }

      document.getElementById('audit-table-body').innerHTML = `
        <table class="data-table">
          <thead>
            <tr>
              <th>Seq</th>
              <th>Timestamp (UTC)</th>
              <th>Actor ID</th>
              <th>Event Type</th>
              <th>Block Hash (SHA-256)</th>
              <th>Previous Link Hash</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    } catch (err) {
      document.getElementById('audit-table-body').innerHTML = `
        <div style="padding: 24px; text-align: center; color: var(--severity-deficiency-fg);">Failed to load audit ledger: ${esc(err.message)}</div>
      `;
    }
  }

  async verifyChain() {
    const btn = document.getElementById('btn-verify-chain-now');
    btn.disabled = true;
    btn.textContent = 'Verifying Hash Chain...';

    try {
      const res = await api.verifyAuditChain();
      const report = res.data;

      const banner = document.getElementById('chain-status-banner');
      const title = document.getElementById('chain-status-text');
      const detail = document.getElementById('chain-detail-text');
      const evaluated = document.getElementById('chain-evaluated-count');

      if (report.is_valid) {
        banner.style.backgroundColor = 'var(--status-verified-bg)';
        banner.style.borderColor = 'var(--status-verified-border)';
        title.textContent = `Cryptographic Audit Chain Intact: All ${report.events_evaluated} Events Mathematically Verified in ${res.elapsed} ms`;
        title.style.color = 'var(--status-verified-fg)';
        detail.textContent = `Genesis: ${report.genesis_hash.slice(0, 8)}... • Tip Hash: ${report.latest_hash.slice(0, 16)}...`;
        evaluated.textContent = `${report.events_evaluated}/${report.events_evaluated} Valid`;
        window.appToast.show(`Chain Verified: All ${report.events_evaluated} blocks valid!`);
      } else {
        banner.style.backgroundColor = 'var(--status-mismatch-bg)';
        banner.style.borderColor = 'var(--status-mismatch-border)';
        title.textContent = `TAMPERING DETECTED at Block #${report.corrupted_sequence}!`;
        title.style.color = 'var(--status-mismatch-fg)';
        detail.textContent = `${report.detail} Event ID: ${report.corrupted_event_id}`;
        evaluated.textContent = `CORRUPTED AT #${report.corrupted_sequence}`;
        window.appToast.show(`Audit Tampering Detected at Block #${report.corrupted_sequence}!`, 'danger');
      }
    } catch (err) {
      window.appToast.show(`Verification error: ${err.message}`, 'danger');
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ Verify Hash Chain';
    }
  }

  async simulateTamper() {
    try {
      const res = await api.simulateAuditTamper();
      window.appToast.show(`Simulated tampering on Block #${res.data.tampered_sequence}! Re-verifying...`, 'warning');
      document.getElementById('btn-restore-chain').style.display = 'inline-block';
      await this.loadEvents();
      await this.verifyChain();
    } catch (err) {
      window.appToast.show(`Tamper simulation failed: ${err.message}`, 'danger');
    }
  }

  async restoreChain() {
    try {
      await api.restoreAuditChain();
      window.appToast.show('Audit chain restored to signed state. Re-verifying...', 'success');
      document.getElementById('btn-restore-chain').style.display = 'none';
      await this.loadEvents();
      await this.verifyChain();
    } catch (err) {
      window.appToast.show(`Restore failed: ${err.message}`, 'danger');
    }
  }
}
