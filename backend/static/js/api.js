/**
 * PRAMAAN-AI API Client
 * Clean, typed HTTP client communicating with FastAPI backend.
 * Enforces server-validated demo session authentication.
 */

export class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.sessionToken = (typeof localStorage !== 'undefined') ? localStorage.getItem('pramaan_session_token') : null;
    this.currentUser = (typeof localStorage !== 'undefined') ? JSON.parse(localStorage.getItem('pramaan_user') || 'null') : null;
  }

  setSession(sessionToken, user) {
    this.sessionToken = sessionToken;
    this.currentUser = user;
    if (typeof localStorage !== 'undefined') {
      if (sessionToken) {
        localStorage.setItem('pramaan_session_token', sessionToken);
        localStorage.setItem('pramaan_user', JSON.stringify(user));
      } else {
        localStorage.removeItem('pramaan_session_token');
        localStorage.removeItem('pramaan_user');
      }
    }
  }

  async ensureSession(defaultUserId = 'usr-officer-01') {
    if (this.sessionToken) {
      try {
        const me = await this.getMe();
        this.currentUser = me.data;
        return this.currentUser;
      } catch (e) {
        this.setSession(null, null);
      }
    }
    const res = await this.createSession(defaultUserId);
    this.setSession(res.data.session_token, res.data.user);
    return this.currentUser;
  }

  async _request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const startTime = performance.now();
    try {
      const headers = { ...(options.headers || {}) };
      if (!(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }
      if (this.sessionToken && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${this.sessionToken}`;
      }

      const response = await fetch(url, {
        ...options,
        headers
      });

      const elapsed = Math.round(performance.now() - startTime);

      if (!response.ok) {
        let errorData = null;
        try {
          errorData = await response.json();
        } catch (_) {}
        const errorMsg = errorData?.detail || `HTTP ${response.status} on ${endpoint}`;
        const error = new Error(errorMsg);
        error.status = response.status;
        error.data = errorData;
        error.elapsed = elapsed;
        throw error;
      }

      const data = await response.json();
      return { data, elapsed, status: response.status };
    } catch (err) {
      if (!err.elapsed) {
        err.elapsed = Math.round(performance.now() - startTime);
      }
      throw err;
    }
  }

  // Session Authentication Endpoints
  async createSession(userId = 'usr-officer-01') {
    return this._request('/api/v1/auth/session', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }

  async getMe() {
    return this._request('/api/v1/auth/me');
  }

  async listDemoUsers() {
    return this._request('/api/v1/auth/demo-users');
  }

  async logout() {
    try {
      await this._request('/api/v1/auth/session', { method: 'DELETE' });
    } finally {
      this.setSession(null, null);
    }
  }

  // Health probe
  async getHealth() {
    return this._request('/health');
  }

  // Applications
  async listApplications(category = null, search = null) {
    let query = '';
    const params = new URLSearchParams();
    if (category && category !== 'ALL') params.append('category', category);
    if (search) params.append('search', search);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
    return this._request(`/api/v1/applications${query}`);
  }

  async getApplication(applicationId) {
    return this._request(`/api/v1/applications/${applicationId}`);
  }

  // Overview metrics
  async getOverviewMetrics() {
    return this._request('/api/v1/overview/metrics');
  }

  // Pre-Scrutiny Orchestrator
  // The server reviews its own stored dossier; the client never sends one.
  async runFullReview(applicationId, _ignoredLegacyDossier, rulePackId = 'rp-aicte-aph-2024-eoa', rulePackVersion = '1.0.0') {
    return this._request(`/api/v1/applications/${applicationId}/full-review`, {
      method: 'POST',
      body: JSON.stringify({ rule_pack_id: rulePackId, rule_pack_version: rulePackVersion })
    });
  }

  async createApplication(payload) {
    return this._request('/api/v1/applications', { method: 'POST', body: JSON.stringify(payload) });
  }

  async _fetchText(endpoint) {
    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: this.sessionToken ? { Authorization: `Bearer ${this.sessionToken}` } : {}
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (e) { /* non-JSON error body */ }
      throw new Error(detail);
    }
    return res.text();
  }

  getScrutinyReportHtml(applicationId) { return this._fetchText(`/api/v1/applications/${applicationId}/scrutiny-report`); }
  getDeficiencyLetterText(applicationId) { return this._fetchText(`/api/v1/applications/${applicationId}/deficiency-letter`); }

  async getLatestReviewReport(applicationId) {
    return this._request(`/api/v1/applications/${applicationId}/full-review/latest`);
  }

  async verifyReviewCoverage(reviewId) {
    return this._request(`/api/v1/review-runs/${reviewId}/coverage-audit`, {
      method: 'POST'
    });
  }

  // Cryptographic Audit Ledger
  async verifyAuditChain() {
    return this._request('/api/v1/audit/verify-chain', {
      method: 'POST'
    });
  }

  async getAuditEvents(applicationId) {
    return this._request(`/api/v1/applications/${applicationId}/audit-events`);
  }

  async recordReviewAction(findingId, actionType, justificationReason, actorId = 'usr-officer-01', applicationId = null) {
    return this._request(`/api/v1/findings/${findingId}/review-actions`, {
      method: 'POST',
      body: JSON.stringify({
        action_type: actionType,
        justification_reason: justificationReason,
        actor_id: actorId,
        application_id: applicationId
      })
    });
  }

  // Verification Subsystem
  async listVerificationAdapters() {
    return this._request('/api/v1/verification/adapters');
  }

  async getVerificationFixtures() {
    return this._request('/api/v1/verification/fixtures');
  }

  async verifyDocument(documentId, options = {}) {
    return this._request(`/api/v1/documents/${documentId}/verify`, {
      method: 'POST',
      body: JSON.stringify({
        adapter_id: options.adapter_id || null,
        method: options.method || null,
        reference_id: options.reference_id || null,
        max_retries: options.max_retries || 3,
        simulate_retry: Boolean(options.simulate_retry),
        context: options.context || {},
        actor_id: options.actor_id || 'usr-officer-01'
      })
    });
  }

  async getDocumentVerificationAttempts(documentId) {
    return this._request(`/api/v1/documents/${documentId}/verification-attempts`);
  }

  async getVerificationAttempt(attemptId) {
    return this._request(`/api/v1/verification/attempts/${attemptId}`);
  }

  async toggleVerificationAdapter(adapterId, enabled) {
    return this._request(`/api/v1/verification/adapters/${adapterId}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ enabled })
    });
  }

  // Duplicates & Historical Comparison
  async getHistoricalComparison(applicationId) {
    return this._request(`/api/v1/applications/${applicationId}/historical-comparison`);
  }

  async listInstitutionSnapshots(institutionId) {
    return this._request(`/api/v1/historical/snapshots/${institutionId}`);
  }

  async scanDuplicates(applicationId) {
    return this._request(`/api/v1/duplicates/scan/${applicationId}`);
  }

  async listDuplicateMatches() {
    return this._request('/api/v1/duplicates/matches');
  }

  async getDuplicateSideBySide(matchId) {
    return this._request(`/api/v1/duplicates/matches/${matchId}/side-by-side`);
  }

  async recordDuplicateVerdict(matchId, verdict, notes = '', actorId = 'usr-officer-01') {
    return this._request(`/api/v1/duplicates/matches/${matchId}/verdict`, {
      method: 'POST',
      body: JSON.stringify({
        verdict,
        notes,
        actor_id: actorId
      })
    });
  }

  // Audit Tampering Test & Limitations
  async simulateAuditTamper(sequence = null) {
    return this._request('/api/v1/audit/simulate-tamper', {
      method: 'POST',
      body: JSON.stringify({ sequence })
    });
  }

  async restoreAuditChain() {
    return this._request('/api/v1/audit/restore-chain', {
      method: 'POST'
    });
  }

  async getAuditLimitationStatement() {
    return this._request('/api/v1/audit/limitation-statement');
  }

  // Protected Documents & Uploads
  async getDocument(documentId) {
    return this._request(`/api/v1/documents/${documentId}`);
  }

  async uploadDocument(file, documentType, applicationId) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    formData.append('application_id', applicationId);
    return this._request('/api/v1/documents/upload', {
      method: 'POST',
      body: formData
    });
  }

  async extractDocument(documentId) {
    return this._request(`/api/v1/documents/${documentId}/extract`, {
      method: 'POST'
    });
  }

  async getDocumentPageView(documentId, pageNumber = 1) {
    const endpoint = `/api/v1/documents/${encodeURIComponent(documentId)}/pages/${encodeURIComponent(pageNumber)}/view`;
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: this.sessionToken ? { Authorization: `Bearer ${this.sessionToken}` } : {}
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = body?.detail || detail;
      } catch (_) { /* response wasn't JSON */ }
      const error = new Error(detail || `HTTP ${response.status} on ${endpoint}`);
      error.status = response.status;
      throw error;
    }
    return response.blob();
  }

  async getRetentionPolicy() {
    return this._request('/api/v1/documents/retention-policy');
  }
}

export const api = new ApiClient();
