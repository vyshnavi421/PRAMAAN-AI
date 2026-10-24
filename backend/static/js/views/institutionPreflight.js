/**
 * PRAMAAN-AI Institution Pre-Flight Diagnostic View Controller
 */
import { api } from '../api.js';
import { store } from '../state.js';

export class InstitutionPreflightView {
  constructor(container) {
    this.container = container;
  }

  async render() {
    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--cobalt-600); margin-bottom: 2px;">
            Applicant Portal • Pre-Submission Diagnostic
          </div>
          <h1 class="page-title">Institution Pre-Flight Compliance Diagnostic</h1>
          <p class="page-desc">Test your application dossier against AICTE APH norms prior to formal submission to prevent deficiency notices</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button id="btn-run-preflight" class="btn btn-primary">Run Pre-Flight Diagnostic</button>
          <button id="btn-submit-formal" class="btn btn-outline" disabled title="Fix deficiencies before submitting">Formal Submit to AICTE</button>
        </div>
      </div>

      <!-- Diagnostic Results Banner -->
      <div id="preflight-results-banner" style="display: none; padding: 14px 18px; border-radius: var(--radius-md); margin-bottom: var(--space-5);"></div>

      <!-- Upload Checklist Table -->
      <div class="table-card">
        <div class="table-toolbar">
          <div>
            <span style="font-weight: 700; font-size: 14px; color: var(--navy-950);">Mandatory EoA Document Checklist</span>
            <div style="font-size: 11px; color: var(--slate-500);">AICTE Approval Process Handbook (APH) 2024–2027 Chapter II Appendix 16</div>
          </div>
          <span class="badge badge-verified">5 REQUIRED TYPES</span>
        </div>
        <div style="overflow-x: auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Document Type</th>
                <th>Prescribed Statutory Format</th>
                <th>Uploaded File</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Affidavit Format A-100</strong></td>
                <td>₹100 non-judicial stamp paper notarized</td>
                <td>affidavit_general.pdf (1.2 MB)</td>
                <td><span class="badge badge-verified">READY</span></td>
                <td><button class="btn btn-outline btn-sm">Replace</button></td>
              </tr>
              <tr>
                <td><strong>Fire Safety NOC</strong></td>
                <td>State Fire & Emergency Services valid certificate</td>
                <td>fire_safety_noc.pdf (2.1 MB)</td>
                <td><span id="preflight-fire-badge" class="badge badge-expired">EXPIRED (2024)</span></td>
                <td><button class="btn btn-outline btn-sm">Upload Renewal</button></td>
              </tr>
              <tr>
                <td><strong>Land Use Certificate</strong></td>
                <td>Issued by Competent Revenue Authority</td>
                <td>land_use_cert.pdf (3.8 MB)</td>
                <td><span class="badge badge-verified">READY</span></td>
                <td><button class="btn btn-outline btn-sm">Replace</button></td>
              </tr>
              <tr>
                <td><strong>Architect Area Certificate</strong></td>
                <td>Signed by Council of Architecture registered architect</td>
                <td>architect_plan.pdf (4.5 MB)</td>
                <td><span class="badge badge-verified">READY</span></td>
                <td><button class="btn btn-outline btn-sm">Replace</button></td>
              </tr>
              <tr>
                <td><strong>Governing Body Resolution</strong></td>
                <td>Trust/Society resolution approving proposed intake</td>
                <td>governing_body_res.pdf (1.1 MB)</td>
                <td><span class="badge badge-verified">READY</span></td>
                <td><button class="btn btn-outline btn-sm">Replace</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;

    document.getElementById('btn-run-preflight').onclick = () => this.runPreflight();
  }

  runPreflight() {
    const banner = document.getElementById('preflight-results-banner');
    banner.style.display = 'block';
    banner.style.backgroundColor = 'var(--severity-deficiency-bg)';
    banner.style.border = '1px solid var(--severity-deficiency-border)';
    banner.style.color = 'var(--severity-deficiency-fg)';

    banner.innerHTML = `
      <div style="display: flex; gap: 10px; align-items: flex-start;">
        <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
        <div>
          <strong style="font-size: 14px;">Pre-Flight Check: 1 Statutory Deficiency Detected</strong>
          <div style="font-size: 12px; margin-top: 4px; line-height: 1.5;">
            <strong>RULE-APH-EXP-003:</strong> The uploaded Fire Safety NOC expired on <strong>14/01/2024</strong>. AICTE regulations require all safety certificates to remain valid through the academic cutoff date (30/06/2026).
            <br>
            <em>Remediation Tip:</em> Upload a renewed certificate or the official treasury challan receipt for renewal before submitting to avoid scrutiny rejection.
          </div>
        </div>
      </div>
    `;

    window.appToast.show("Pre-flight diagnostic completed: 1 deficiency flagged for applicant review.", "warning");
  }
}
