/**
 * PRAMAAN-AI Reviewer Queue View Controller
 */
import { api } from '../api.js';
import { esc } from '../util.js';
import { store } from '../state.js';

export class ReviewerQueueView {
  constructor(container) {
    this.container = container;
    this.applications = [];
    this.loading = false;
    this.error = null;
  }

  async render() {
    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Scrutiny Officer Work Queue</h1>
          <p class="page-desc">Assigned institutional applications awaiting AICTE regulatory scrutiny • Regional Office</p>
        </div>
        <div>
          <button id="btn-new-application" class="btn btn-primary">＋ New Application</button>
        </div>
      </div>

      <div class="table-card">
        <!-- Search & Filter Controls -->
        <div class="table-toolbar">
          <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
            <input 
              type="text" 
              id="queue-search" 
              placeholder="Search by App ID, College Name..." 
              style="padding: 6px 12px; font-size: 13px; border: 1px solid var(--slate-300); border-radius: var(--radius-md); width: 260px;"
            />
            <select id="queue-category-select" style="padding: 6px 12px; font-size: 13px; border: 1px solid var(--slate-300); border-radius: var(--radius-md); background: white;">
              <option value="ALL">All Categories</option>
              <option value="EXTENSION_OF_APPROVAL">Extension of Approval (EoA)</option>
              <option value="NEW_INSTITUTION">New Institution</option>
            </select>
          </div>
          <div id="queue-count-badge" class="metric-meta" style="font-weight: 600;">Loading cases...</div>
        </div>

        <div id="queue-table-body" style="overflow-x: auto;">
          <div style="padding: 16px;">
            <div class="skeleton-row">
              <span class="skeleton" style="width: 140px; height: 16px;"></span>
              <span class="skeleton" style="width: 280px; height: 16px;"></span>
              <span class="skeleton" style="width: 80px; height: 16px;"></span>
              <span class="skeleton" style="width: 60px; height: 16px;"></span>
              <span class="skeleton" style="width: 120px; height: 16px;"></span>
              <span class="skeleton" style="width: 100px; height: 16px;"></span>
            </div>
            <div class="skeleton-row">
              <span class="skeleton" style="width: 140px; height: 16px;"></span>
              <span class="skeleton" style="width: 260px; height: 16px;"></span>
              <span class="skeleton" style="width: 80px; height: 16px;"></span>
              <span class="skeleton" style="width: 60px; height: 16px;"></span>
              <span class="skeleton" style="width: 120px; height: 16px;"></span>
              <span class="skeleton" style="width: 100px; height: 16px;"></span>
            </div>
            <div class="skeleton-row">
              <span class="skeleton" style="width: 140px; height: 16px;"></span>
              <span class="skeleton" style="width: 310px; height: 16px;"></span>
              <span class="skeleton" style="width: 80px; height: 16px;"></span>
              <span class="skeleton" style="width: 60px; height: 16px;"></span>
              <span class="skeleton" style="width: 120px; height: 16px;"></span>
              <span class="skeleton" style="width: 100px; height: 16px;"></span>
            </div>
          </div>
        </div>
      </div>
    `;

    document.getElementById('queue-search').oninput = (e) => {
      this.filterAndRenderTable(e.target.value, document.getElementById('queue-category-select').value);
    };

    document.getElementById('queue-category-select').onchange = (e) => {
      this.filterAndRenderTable(document.getElementById('queue-search').value, e.target.value);
    };

    document.getElementById('btn-new-application').onclick = () => this.openNewApplicationDialog();

    await this.fetchApplications();
  }

  openNewApplicationDialog() {
    const isInstitution = api.currentUser?.role === 'INSTITUTION_USER';
    if (!['INSTITUTION_USER', 'REVIEWER'].includes(api.currentUser?.role)) {
      window.appToast.show('Only institution users or scrutiny officers can open a dossier.', 'warning');
      return;
    }
    const dlg = document.createElement('dialog');
    dlg.setAttribute('aria-label', 'New application');
    dlg.style.cssText = 'border:1px solid var(--slate-300);border-radius:12px;padding:20px;width:min(440px,92vw)';
    dlg.innerHTML = `
      <form method="dialog" id="new-app-form" style="display:grid;gap:10px">
        <h2 style="margin:0;font-size:16px">New application dossier</h2>
        <p class="metric-meta" style="margin:0">Opens an empty DEMO dossier. Upload documents next, then run pre-scrutiny.</p>
        <label>Institution name<input id="na-name" required minlength="3" maxlength="200" style="width:100%;padding:6px"></label>
        ${isInstitution ? '' : '<label>Institution ID (e.g. inst-demo-09)<input id="na-inst" required pattern="[a-z0-9][a-z0-9\\-]{2,63}" style="width:100%;padding:6px"></label>'}
        <label>Category
          <select id="na-cat" style="width:100%;padding:6px">
            <option value="EXTENSION_OF_APPROVAL">Extension of Approval</option>
            <option value="NEW_INSTITUTION">New Institution</option>
            <option value="INCREASE_IN_INTAKE">Increase in Intake</option>
            <option value="NEW_COURSE">New Course</option>
          </select>
        </label>
        <label>Declared total intake (optional)<input id="na-intake" type="number" min="0" style="width:100%;padding:6px"></label>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button type="button" class="btn btn-outline" id="na-cancel">Cancel</button>
          <button type="submit" class="btn btn-primary">Create dossier</button>
        </div>
      </form>`;
    document.body.appendChild(dlg);
    const close = () => { dlg.close(); dlg.remove(); };
    dlg.querySelector('#na-cancel').onclick = close;
    dlg.querySelector('#new-app-form').onsubmit = async (ev) => {
      ev.preventDefault();
      const intake = dlg.querySelector('#na-intake').value;
      const body = {
        institution_name: dlg.querySelector('#na-name').value.trim(),
        category: dlg.querySelector('#na-cat').value,
      };
      if (intake) body.total_intake = Number(intake);
      const inst = dlg.querySelector('#na-inst');
      if (inst) body.institution_id = inst.value.trim();
      try {
        const res = await api.createApplication(body);
        close();
        window.appToast.show(`Dossier ${res.data.application_number} created.`);
        await this.fetchApplications();
        window.appRouter.openCase(res.data.application_id);
      } catch (err) {
        window.appToast.show(`Could not create dossier: ${err.message}`, 'danger');
      }
    };
    dlg.showModal();
  }

  async fetchApplications() {
    this.loading = true;
    try {
      const res = await api.listApplications();
      this.applications = res.data || [];
      this.loading = false;
      this.filterAndRenderTable('', 'ALL');
    } catch (err) {
      this.loading = false;
      this.error = err.message;
      document.getElementById('queue-table-body').innerHTML = `
        <div style="padding: 24px;">
          <div class="error-card">
            <svg width="22" height="22" fill="currentColor" viewBox="0 0 20 20" style="flex-shrink: 0; color: var(--severity-deficiency-fg);">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
            <div>
              <div class="error-card-title">Scrutiny Queue Retrieval Failed (RFC 7807 Standard Error)</div>
              <div class="error-card-detail">Failed to communicate with the local repository service: ${esc(err.message)}</div>
              <div class="error-card-meta">Instance: /api/v1/applications • Status: Service Unavailable</div>
              <button class="btn btn-primary btn-sm" style="margin-top: 12px;" onclick="window.appRouter.views.queue.fetchApplications()">Retry Loading Queue</button>
            </div>
          </div>
        </div>
      `;
    }
  }

  filterAndRenderTable(search, category) {
    let list = this.applications;
    if (category && category !== 'ALL') {
      list = list.filter(a => a.category === category);
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(a => 
        a.application_number.toLowerCase().includes(q) ||
        a.institution_name.toLowerCase().includes(q) ||
        a.institution_id.toLowerCase().includes(q)
      );
    }

    document.getElementById('queue-count-badge').textContent = `Showing ${list.length} assigned dossier${list.length === 1 ? '' : 's'}`;

    if (list.length === 0) {
      document.getElementById('queue-table-body').innerHTML = `
        <div class="empty-state">
          <svg class="empty-state-icon" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"></path>
          </svg>
          <div class="empty-state-title">No Applications Found in Queue</div>
          <div class="empty-state-desc">No assigned dossiers match the current search filters. You can clear the search or change the category filter to view all applications.</div>
          <button class="btn btn-outline btn-sm" onclick="document.getElementById('queue-search').value=''; document.getElementById('queue-category-select').value='ALL'; window.appRouter.views.queue.filterAndRenderTable('', 'ALL');">
            Clear Search & Filters
          </button>
        </div>
      `;
      return;
    }

    let rowsHtml = '';
    for (const app of list) {
      let badgeClass = 'badge-verified';
      let badgeLabel = 'ALL CLEAR';

      if (app.status_tag === 'DEFICIENCY_EXPIRED') {
        badgeClass = 'badge-expired';
        badgeLabel = 'EXPIRED NOC';
      } else if (app.status_tag === 'ANOMALY_REUSE') {
        badgeClass = 'badge-anomaly';
        badgeLabel = 'REUSE SIGNAL';
      } else if (app.status_tag === 'SOURCE_UNAVAILABLE') {
        badgeClass = 'badge-source-unavailable';
        badgeLabel = 'SOURCE OUTAGE';
      } else if (app.status_tag === 'ANOMALY_MISMATCH') {
        badgeClass = 'badge-mismatch';
        badgeLabel = 'INTAKE MISMATCH';
      } else if (app.status_tag === 'ANOMALY_INTAKE') {
        badgeClass = 'badge-anomaly';
        badgeLabel = 'INTAKE DRIFT';
      } else if (app.status_tag === 'NOT_YET_REVIEWED') {
        // Never show "ALL CLEAR" for a dossier no review has covered.
        badgeClass = 'badge-pending';
        badgeLabel = app.workflow_status === 'DRAFT' ? 'DRAFT · NOT REVIEWED' : 'NOT YET REVIEWED';
      }

      rowsHtml += `
        <tr 
          style="cursor: pointer;" 
          tabindex="0"
          role="link"
          aria-label="Inspect ${esc(app.application_number)} ${esc(app.institution_name)}"
          onclick="window.appRouter.openCase('${esc(app.application_id)}')"
          onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault(); window.appRouter.openCase('${esc(app.application_id)}');}"
        >
          <td><strong style="color: var(--cobalt-700);">${esc(app.application_number)}</strong></td>
          <td style="max-width: 320px;">
            <div style="font-weight: 600; color: var(--slate-900); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${esc(app.institution_name)}">${esc(app.institution_name)}</div>
            <div style="font-size: 11px; color: var(--slate-500);">${esc(app.institution_id)}</div>
          </td>
          <td><span class="mono-hash">${app.category === 'EXTENSION_OF_APPROVAL' ? 'EoA' : 'New Inst.'}</span></td>
          <td>${app.document_count} files</td>
          <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
          <td><button class="btn btn-outline btn-sm" tabindex="-1">Inspect Dossier →</button></td>
        </tr>
      `;
    }

    document.getElementById('queue-table-body').innerHTML = `
      <table class="data-table" role="table" aria-label="Assigned Institutional Applications">
        <thead>
          <tr>
            <th scope="col">Application ID</th>
            <th scope="col">Institution Name</th>
            <th scope="col">Category</th>
            <th scope="col">Documents</th>
            <th scope="col">Preliminary Status</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    `;
  }
}

