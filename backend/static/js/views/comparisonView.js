/**
 * PRAMAAN-AI Change-Aware Historical & Cross-Application Reuse View Controller
 * Features:
 * 1. Change-Aware Historical Review against authorised / synthetic baseline snapshots
 *    - Name and address normalisation (abbreviations, spacing)
 *    - Borderline variations routed to review rather than false violations
 *    - Intake expansion tracking (+33.3%, etc.) under RULE-AICTE-HIST-006 (never as fraud!)
 *    - First-time application handling without errors
 * 2. Cross-Application Document Reuse Detection
 *    - Exact binary collisions (SHA-256)
 *    - Approximate text similarity and generic boilerplate templates
 *    - Interactive side-by-side document viewer
 *    - 1-click authorized reviewer resolution buttons
 */
import { api } from '../api.js';
import { esc } from '../util.js';
import { store } from '../state.js';

export class ComparisonView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'historical'; // 'historical' or 'duplicates'
    this.selectedAppId = 'app-case-clean';
    this.historicalReport = null;
    this.duplicateMatches = [];
    this.selectedMatchId = null;
    this.sideBySideData = null;
  }

  getBadgeClass(changeType) {
    switch (changeType) {
      case 'IDENTICAL': return 'badge-compliant';
      case 'NORMALIZED_MATCH': return 'badge-verified';
      case 'INCREASE_REQUESTED': return 'badge-anomaly';
      case 'BORDERLINE_REVIEW': return 'badge-source-unavailable';
      case 'LEGITIMATE_VARIATION': return 'badge-pending';
      case 'FIRST_TIME_APPLICATION': return 'badge-verified';
      default: return 'badge-inconclusive';
    }
  }

  async render() {
    const s = store.getState();
    if (s.activeApplicationId && s.activeApplicationId !== 'app-case-clean') {
      this.selectedAppId = s.activeApplicationId;
    }

    this.container.innerHTML = `
      <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
        <!-- Header -->
        <div class="page-header" style="margin-bottom: 20px;">
          <div>
            <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--cobalt-600); margin-bottom: 2px;">
              Cross-Dossier & Historical Intelligence
            </div>
            <h1 class="page-title">Change-Aware Review & Cross-Application Document Reuse</h1>
            <p class="page-desc">Trace institutional drift across academic years, evaluate parameter normalisation, and inspect document collisions side-by-side</p>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <select id="select-comp-app" class="form-control" style="font-size: 12px; font-weight: 600; padding: 6px 12px;">
              <option value="app-case-clean">Apex Institute (app-case-clean) · Baseline Compliant</option>
              <option value="app-case-historical">Bharat Polytechnic (app-case-historical) · Intake Expansion (+50%)</option>
              <option value="app-case-reuse">Vidya Polytechnic (app-case-reuse) · Architect File Reuse</option>
              <option value="app-case-intake-mismatch">City College (app-case-intake-mismatch) · 240 Intake</option>
              <option value="app-brand-new">Zenith Tech (app-brand-new) · First-Time Application</option>
            </select>
          </div>
        </div>

        <!-- Statutory Truthfulness Guardrail Banner -->
        <div style="background-color: var(--status-source-unavail-bg); border: 1px solid var(--status-source-unavail-border); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 24px; display: flex; align-items: flex-start; gap: 14px;">
          <svg width="22" height="22" fill="var(--status-source-unavail-fg)" viewBox="0 0 20 20" style="flex-shrink: 0; margin-top: 2px;">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
          </svg>
          <div style="font-size: 13px; color: var(--status-source-unavail-fg); line-height: 1.5;">
            <strong>Statutory Truthfulness Guardrail:</strong> Parameter changes (such as student intake expansion) or document collisions (such as shared building plans under the same Educational Trust) are <strong>preliminary reviewer advisories</strong>. The system <strong>never autonomously declares fraud or levys penalties</strong>. Normalised administrative abbreviations are recognized legitimately.
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-nav" style="margin-bottom: 20px;">
          <button id="tab-btn-historical" class="tab-btn ${this.activeTab === 'historical' ? 'active' : ''}">
            Year-over-Year Historical Baseline Comparison
          </button>
          <button id="tab-btn-duplicates" class="tab-btn ${this.activeTab === 'duplicates' ? 'active' : ''}">
            Cross-Application Document Reuse & Side-by-Side Reviewer
          </button>
        </div>

        <!-- Tab 1: Historical Review -->
        <div id="tab-pane-historical" style="display: ${this.activeTab === 'historical' ? 'block' : 'none'};">
          <div class="table-card">
            <div class="table-toolbar" style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span id="hist-title" style="font-weight: 700; font-size: 15px; color: var(--navy-950);">Year-over-Year Parameter Drift Analysis</span>
                <div id="hist-subtitle" style="font-size: 11px; color: var(--slate-500);">Loading historical baseline...</div>
              </div>
              <span id="hist-badge" class="badge badge-verified">HISTORICAL BASELINE LOADED</span>
            </div>
            
            <!-- Summary Stats Grid -->
            <div id="hist-summary-grid" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; padding: 16px; background: #f8fafc; border-bottom: 1px solid var(--slate-200);">
              <div style="text-align: center;">
                <div style="font-size: 10px; font-weight: 700; color: var(--slate-500); text-transform: uppercase;">Parameters Evaluated</div>
                <div id="stat-total" style="font-size: 20px; font-weight: 700; color: var(--navy-950); margin-top: 2px;">0</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 10px; font-weight: 700; color: var(--severity-compliant-fg); text-transform: uppercase;">Identical</div>
                <div id="stat-identical" style="font-size: 20px; font-weight: 700; color: var(--severity-compliant-fg); margin-top: 2px;">0</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 10px; font-weight: 700; color: var(--cobalt-600); text-transform: uppercase;">Normalized Match</div>
                <div id="stat-normalized" style="font-size: 20px; font-weight: 700; color: var(--cobalt-600); margin-top: 2px;">0</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 10px; font-weight: 700; color: var(--saffron-600); text-transform: uppercase;">Planned Expansion</div>
                <div id="stat-changed" style="font-size: 20px; font-weight: 700; color: var(--saffron-600); margin-top: 2px;">0</div>
              </div>
              <div style="text-align: center;">
                <div style="font-size: 10px; font-weight: 700; color: var(--status-source-unavail-fg); text-transform: uppercase;">Borderline Review</div>
                <div id="stat-borderline" style="font-size: 20px; font-weight: 700; color: var(--status-source-unavail-fg); margin-top: 2px;">0</div>
              </div>
            </div>

            <!-- Deltas Table -->
            <div style="overflow-x: auto;">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Statutory Parameter</th>
                    <th>Approved Historical Baseline</th>
                    <th>Submitted Dossier (Current)</th>
                    <th>Variance / Delta</th>
                    <th>Classification Status</th>
                    <th>Statutory Reviewer Guidance</th>
                  </tr>
                </thead>
                <tbody id="hist-tbody">
                  <tr><td colspan="6" style="text-align: center; color: var(--slate-500); padding: 20px;">Loading historical comparison...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Tab 2: Cross-Application Duplicates & Side-by-Side Reviewer -->
        <div id="tab-pane-duplicates" style="display: ${this.activeTab === 'duplicates' ? 'block' : 'none'};">
          <div style="display: grid; grid-template-columns: 1fr; gap: 20px;">
            
            <!-- Matches Table -->
            <div class="table-card">
              <div class="table-toolbar" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <span style="font-weight: 700; font-size: 15px; color: var(--navy-950);">Detected Document Reuse & Similarity Signals</span>
                  <div style="font-size: 11px; color: var(--slate-500);">Binary SHA-256 collisions, approximate text overlap, and generic boilerplate templates</div>
                </div>
                <button id="btn-rescan-dups" class="btn btn-outline btn-sm">Rescan Cross-Dossier Index</button>
              </div>
              <div style="overflow-x: auto;">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Collision Type</th>
                      <th>Method</th>
                      <th>Similarity Score</th>
                      <th>Source Document</th>
                      <th>Conflicting Application</th>
                      <th>Detected Timestamp</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody id="dups-tbody">
                    <tr><td colspan="7" style="text-align: center; color: var(--slate-500); padding: 20px;">Scanning for cross-application file reuse...</td></tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Side-by-Side Reviewer Workspace -->
            <div id="side-by-side-card" class="table-card" style="display: none; padding: 20px;">
              <div style="border-bottom: 1px solid var(--slate-200); padding-bottom: 14px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--cobalt-600);">Side-by-Side Reviewer Workspace</div>
                  <h3 id="sbs-title" style="font-size: 16px; font-weight: 700; color: var(--navy-950); margin: 2px 0 0 0;">Document Comparison</h3>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                  <span id="sbs-match-badge" class="badge badge-anomaly">EXACT BINARY COLLISION</span>
                  <button id="btn-close-sbs" class="btn btn-outline btn-sm">Close Viewer ✕</button>
                </div>
              </div>

              <!-- Two-Pane Layout -->
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <!-- Left Pane: Source Document -->
                <div style="background: #f8fafc; border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 16px;">
                  <div style="font-size: 10px; font-weight: 700; color: var(--cobalt-600); text-transform: uppercase; margin-bottom: 4px;">Primary Document (Current Filing)</div>
                  <div id="sbs-src-name" style="font-size: 14px; font-weight: 700; color: var(--navy-950);">-</div>
                  <div id="sbs-src-inst" style="font-size: 12px; color: var(--slate-600); margin: 2px 0 8px 0;">-</div>
                  
                  <div style="background: white; border: 1px solid var(--slate-200); border-radius: 4px; padding: 8px; margin-bottom: 10px;">
                    <div style="font-size: 10px; font-weight: 700; color: var(--slate-500);">SHA-256 Digest</div>
                    <div id="sbs-src-hash" class="mono-hash" style="font-size: 10px; word-break: break-all;">-</div>
                  </div>

                  <div style="font-size: 11px; font-weight: 700; color: var(--slate-700); margin-bottom: 4px;">Extracted Content Stream:</div>
                  <div id="sbs-src-preview" style="background: white; border: 1px solid var(--slate-200); border-radius: 4px; padding: 10px; font-size: 11px; color: var(--slate-800); max-height: 180px; overflow-y: auto; line-height: 1.5; font-family: var(--font-mono); white-space: pre-wrap;">-</div>
                </div>

                <!-- Right Pane: Target Document -->
                <div style="background: #f8fafc; border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 16px;">
                  <div style="font-size: 10px; font-weight: 700; color: var(--saffron-600); text-transform: uppercase; margin-bottom: 4px;">Conflicting Document (External Filing)</div>
                  <div id="sbs-tgt-name" style="font-size: 14px; font-weight: 700; color: var(--navy-950);">-</div>
                  <div id="sbs-tgt-inst" style="font-size: 12px; color: var(--slate-600); margin: 2px 0 8px 0;">-</div>
                  
                  <div style="background: white; border: 1px solid var(--slate-200); border-radius: 4px; padding: 8px; margin-bottom: 10px;">
                    <div style="font-size: 10px; font-weight: 700; color: var(--slate-500);">SHA-256 Digest</div>
                    <div id="sbs-tgt-hash" class="mono-hash" style="font-size: 10px; word-break: break-all;">-</div>
                  </div>

                  <div style="font-size: 11px; font-weight: 700; color: var(--slate-700); margin-bottom: 4px;">Extracted Content Stream:</div>
                  <div id="sbs-tgt-preview" style="background: white; border: 1px solid var(--slate-200); border-radius: 4px; padding: 10px; font-size: 11px; color: var(--slate-800); max-height: 180px; overflow-y: auto; line-height: 1.5; font-family: var(--font-mono); white-space: pre-wrap;">-</div>
                </div>
              </div>

              <!-- Legitimacy Assessment Notice -->
              <div style="background: #fffbeb; border: 1px solid #fef3c7; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px;">
                <div style="font-size: 11px; font-weight: 700; color: #b45309; text-transform: uppercase;">Statutory Evidentiary Assessment</div>
                <div id="sbs-assessment" style="font-size: 12px; color: #92400e; margin-top: 2px; line-height: 1.4;">-</div>
              </div>

              <!-- Reviewer Action Resolution Bar -->
              <div style="background: white; border: 1px solid var(--slate-200); border-radius: 6px; padding: 14px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-size: 12px; font-weight: 700; color: var(--navy-950);">Record Authorised Officer Resolution:</div>
                  <div style="font-size: 11px; color: var(--slate-500);">Dispatches an immutable audit ledger entry to finalize the anomaly signal.</div>
                </div>
                <div style="display: flex; gap: 8px;">
                  <button class="btn btn-outline btn-sm" onclick="window.appRouter.views.comparison.recordResolution('CONFIRM_SHARED_SPONSORING_TRUST')">Confirm Shared Trust</button>
                  <button class="btn btn-outline btn-sm" onclick="window.appRouter.views.comparison.recordResolution('CONFIRM_COMMON_LICENSED_ARCHITECT')">Confirm Common Architect</button>
                  <button class="btn btn-outline btn-sm" onclick="window.appRouter.views.comparison.recordResolution('ACKNOWLEDGE_GENERIC_STATUTORY_TEMPLATE')">Acknowledge Template</button>
                  <button class="btn btn-primary btn-sm" onclick="window.appRouter.views.comparison.recordResolution('ISSUE_CLARIFICATION_NOTICE')">Issue Clarification</button>
                </div>
              </div>

            </div>

          </div>
        </div>

      </div>
    `;

    this.wireEvents();
    await this.loadHistoricalComparison();
    await this.loadDuplicateMatches();
  }

  wireEvents() {
    const selApp = document.getElementById('select-comp-app');
    const tabHist = document.getElementById('tab-btn-historical');
    const tabDups = document.getElementById('tab-btn-duplicates');
    const btnRescan = document.getElementById('btn-rescan-dups');
    const btnCloseSbs = document.getElementById('btn-close-sbs');

    if (selApp) {
      selApp.value = this.selectedAppId;
      selApp.onchange = (e) => {
        this.selectedAppId = e.target.value;
        this.loadHistoricalComparison();
        this.loadDuplicateMatches();
      };
    }

    if (tabHist) {
      tabHist.onclick = () => {
        this.activeTab = 'historical';
        document.getElementById('tab-pane-historical').style.display = 'block';
        document.getElementById('tab-pane-duplicates').style.display = 'none';
        tabHist.classList.add('active');
        tabDups.classList.remove('active');
      };
    }

    if (tabDups) {
      tabDups.onclick = () => {
        this.activeTab = 'duplicates';
        document.getElementById('tab-pane-historical').style.display = 'none';
        document.getElementById('tab-pane-duplicates').style.display = 'block';
        tabDups.classList.add('active');
        tabHist.classList.remove('active');
      };
    }

    if (btnRescan) {
      btnRescan.onclick = () => {
        this.loadDuplicateMatches();
        window.appToast.show('Cross-dossier index rescanned.');
      };
    }

    if (btnCloseSbs) {
      btnCloseSbs.onclick = () => {
        document.getElementById('side-by-side-card').style.display = 'none';
      };
    }
  }

  async loadHistoricalComparison() {
    const subtitle = document.getElementById('hist-subtitle');
    const tbody = document.getElementById('hist-tbody');

    try {
      if (subtitle) subtitle.textContent = `Evaluating dossier ${this.selectedAppId}...`;
      const res = await api.getHistoricalComparison(this.selectedAppId);
      this.historicalReport = res.data;
      this.renderHistoricalReport();
    } catch (err) {
      console.error('Failed to load historical comparison:', err);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" style="color: var(--severity-deficiency-fg); padding: 16px;">Failed to load comparison: ${esc(err.message)}</td></tr>`;
      }
    }
  }

  renderHistoricalReport() {
    const r = this.historicalReport;
    if (!r) return;

    const subtitle = document.getElementById('hist-subtitle');
    const badge = document.getElementById('hist-badge');
    const tbody = document.getElementById('hist-tbody');

    if (subtitle) {
      subtitle.textContent = r.is_first_time_application
        ? `First-Time Institutional Filing · Academic Year ${esc(r.current_academic_year)}`
        : `Comparing Current Dossier (${esc(r.current_academic_year)}) vs Approved Baseline (${esc(r.baseline_academic_year)})`;
    }

    if (badge) {
      badge.className = r.is_first_time_application ? 'badge badge-verified' : 'badge badge-compliant';
      badge.textContent = r.is_first_time_application ? 'FIRST-TIME FILING' : `BASELINE AY ${r.baseline_academic_year}`;
    }

    // Update stats
    document.getElementById('stat-total').textContent = r.total_parameters_evaluated;
    document.getElementById('stat-identical').textContent = r.identical_count;
    document.getElementById('stat-normalized').textContent = r.normalized_match_count;
    document.getElementById('stat-changed').textContent = r.changed_count;
    document.getElementById('stat-borderline').textContent = r.borderline_review_count;

    if (!r.deltas || r.deltas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--slate-500); padding: 16px;">No statutory parameters evaluated.</td></tr>`;
      return;
    }

    tbody.innerHTML = r.deltas.map(d => {
      const prevVal = d.previous_value !== null ? String(d.previous_value) : '<span style="color: var(--slate-400);">None (New)</span>';
      const currVal = d.current_value !== null ? String(d.current_value) : '<span style="color: var(--slate-400);">Removed</span>';
      const deltaText = d.variance_pct !== null && d.variance_pct !== undefined
        ? `${d.variance_pct > 0 ? '+' : ''}${esc(d.variance_pct)}%`
        : (d.change_type === 'IDENTICAL' ? '0%' : 'Delta Logged');

      return `
        <tr>
          <td>
            <strong>${esc(d.field_label)}</strong>
            <div class="mono-hash" style="font-size: 10px; color: var(--slate-500);">${esc(d.field_key)}</div>
          </td>
          <td>
            <div style="font-weight: 600; color: var(--navy-950);">${prevVal}</div>
            <div style="font-size: 10px; color: var(--slate-500);">${esc(d.source_previous)}</div>
          </td>
          <td>
            <div style="font-weight: 600; color: var(--navy-950);">${currVal}</div>
            <div style="font-size: 10px; color: var(--slate-500);">${esc(d.source_current)}</div>
          </td>
          <td>
            <span style="font-weight: 700; color: ${d.variance_pct && d.variance_pct > 0 ? 'var(--saffron-600)' : 'var(--slate-700)'};">${deltaText}</span>
          </td>
          <td>
            <span class="badge ${this.getBadgeClass(d.change_type)}">${d.change_type.replace(/_/g, ' ')}</span>
          </td>
          <td style="font-size: 11px; color: var(--slate-700); line-height: 1.4; max-width: 320px;">
            ${esc(d.delta_description)}
          </td>
        </tr>
      `;
    }).join('');
  }

  async loadDuplicateMatches() {
    const tbody = document.getElementById('dups-tbody');
    try {
      const res = await api.listDuplicateMatches();
      this.duplicateMatches = res.data || [];
      this.renderDuplicatesTable();
    } catch (err) {
      console.error('Failed to load duplicate matches:', err);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" style="color: var(--severity-deficiency-fg); padding: 16px;">Failed to scan duplicates: ${esc(err.message)}</td></tr>`;
      }
    }
  }

  renderDuplicatesTable() {
    const tbody = document.getElementById('dups-tbody');
    if (!tbody) return;

    if (!this.duplicateMatches || this.duplicateMatches.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--slate-500); padding: 20px;">No cross-application document reuse detected across repository dossiers.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.duplicateMatches.map(m => {
      const matchBadge = m.match_type === 'EXACT_BINARY_MATCH'
        ? '<span class="badge badge-deficiency">EXACT BINARY COLLISION</span>'
        : (m.match_type === 'GENERIC_TEMPLATE'
          ? '<span class="badge badge-verified">GENERIC TEMPLATE</span>'
          : '<span class="badge badge-anomaly">APPROXIMATE SIMILARITY</span>');

      const simPct = `${(m.similarity_score * 100).toFixed(1)}%`;
      const dateStr = new Date(m.detected_at).toLocaleTimeString();

      return `
        <tr>
          <td>${matchBadge}</td>
          <td><span class="mono-hash" style="font-size: 10px;">${esc(m.method)}</span></td>
          <td><strong>${simPct}</strong></td>
          <td>
            <strong>${esc(m.source_doc.original_filename)}</strong>
            <div style="font-size: 10px; color: var(--slate-500);">${esc(m.source_doc.application_id)} (${esc(m.source_doc.institution_name)})</div>
          </td>
          <td>
            <strong>${esc(m.target_doc.original_filename)}</strong>
            <div style="font-size: 10px; color: var(--slate-500);">${esc(m.target_doc.application_id)} (${esc(m.target_doc.institution_name)})</div>
          </td>
          <td style="font-size: 11px; color: var(--slate-500);">${dateStr}</td>
          <td>
            <button class="btn btn-outline btn-sm" onclick="window.appRouter.views.comparison.inspectSideBySide('${esc(m.id)}')">
              Inspect Side-by-Side ▾
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  async inspectSideBySide(matchId) {
    this.selectedMatchId = matchId;
    const card = document.getElementById('side-by-side-card');

    try {
      const res = await api.getDuplicateSideBySide(matchId);
      this.sideBySideData = res.data;

      document.getElementById('sbs-title').textContent = `${this.sideBySideData.source_panel.filename} vs ${this.sideBySideData.target_panel.filename}`;
      
      const badge = document.getElementById('sbs-match-badge');
      badge.textContent = `${this.sideBySideData.match_type} (${(this.sideBySideData.similarity_score * 100).toFixed(1)}%)`;

      // Source panel
      document.getElementById('sbs-src-name').textContent = this.sideBySideData.source_panel.filename;
      document.getElementById('sbs-src-inst').textContent = `${this.sideBySideData.source_panel.institution_name} · ${this.sideBySideData.source_panel.application_id}`;
      document.getElementById('sbs-src-hash').textContent = this.sideBySideData.source_panel.sha256_hash;
      document.getElementById('sbs-src-preview').textContent = this.sideBySideData.source_panel.text_preview || 'Document text extracted.';

      // Target panel
      document.getElementById('sbs-tgt-name').textContent = this.sideBySideData.target_panel.filename;
      document.getElementById('sbs-tgt-inst').textContent = `${this.sideBySideData.target_panel.institution_name} · ${this.sideBySideData.target_panel.application_id}`;
      document.getElementById('sbs-tgt-hash').textContent = this.sideBySideData.target_panel.sha256_hash;
      document.getElementById('sbs-tgt-preview').textContent = this.sideBySideData.target_panel.text_preview || 'Document text extracted.';

      // Assessment
      document.getElementById('sbs-assessment').textContent = this.sideBySideData.legitimacy_assessment;

      card.style.display = 'block';
      card.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      window.appToast.show(`Failed to open side-by-side viewer: ${err.message}`);
    }
  }

  async recordResolution(verdict) {
    if (!this.selectedMatchId) return;

    try {
      await api.recordDuplicateVerdict(this.selectedMatchId, verdict, 'Resolution logged by review officer.');
      window.appToast.show(`Resolution recorded: ${verdict.replace(/_/g, ' ')}`);
      document.getElementById('side-by-side-card').style.display = 'none';
      await this.loadDuplicateMatches();
    } catch (err) {
      window.appToast.show(`Failed to record verdict: ${err.message}`);
    }
  }
}
