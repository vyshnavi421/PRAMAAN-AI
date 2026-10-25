/**
 * PRAMAAN-AI Main Application Coordinator & Router
 * Assembles modular views, keyboard shortcuts, modals, and toasts.
 */
import { api } from './api.js';
import { store } from './state.js';
import { CommandCenterView } from './views/commandCenter.js';
import { ReviewerQueueView } from './views/reviewerQueue.js';
import { CaseFileView } from './views/caseFile.js';
import { EvidenceStudioView } from './views/evidenceStudio.js';
import { VerificationLadderView } from './views/verificationLadder.js';
import { ComparisonView } from './views/comparisonView.js';
import { AuditLedgerView } from './views/auditLedger.js';
import { InstitutionPreflightView } from './views/institutionPreflight.js';

class ToastManager {
  constructor() {
    this.container = document.getElementById('toast-container');
  }

  show(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    if (type === 'danger') toast.style.backgroundColor = 'var(--severity-deficiency-fg)';
    else if (type === 'warning') toast.style.backgroundColor = 'var(--severity-anomaly-fg)';
    const dot = document.createElement('span');
    dot.className = 'health-dot';
    dot.style.cssText = 'background: white; box-shadow: none;';
    const text = document.createElement('span');
    text.textContent = String(message); // textContent: never interpret server/user text as HTML
    toast.append(dot, text);
    toast.setAttribute('role', type === 'danger' ? 'alert' : 'status');
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 200ms ease';
      setTimeout(() => toast.remove(), 200);
    }, 3500);
  }
}

class ModalManager {
  constructor() {
    this.lastFocusedElement = null;
    this.modal = document.getElementById('decision-modal');
    this.bindFocusTrap();
  }

  bindFocusTrap() {
    this.modal?.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        const focusables = Array.from(this.modal.querySelectorAll('button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])'));
        if (focusables.length === 0) return;
        const firstEl = focusables[0];
        const lastEl = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === firstEl) {
          e.preventDefault();
          lastEl.focus();
        } else if (!e.shiftKey && document.activeElement === lastEl) {
          e.preventDefault();
          firstEl.focus();
        }
      }
    });
  }

  openDecisionModal() {
    this.lastFocusedElement = document.activeElement;
    const modal = document.getElementById('decision-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    setTimeout(() => {
      const firstInput = modal.querySelector('input[name="decision-choice"]:checked') || modal.querySelector('button');
      firstInput?.focus();
    }, 60);
  }

  closeDecisionModal() {
    const modal = document.getElementById('decision-modal');
    if (!modal) return;
    modal.style.display = 'none';
    if (this.lastFocusedElement && typeof this.lastFocusedElement.focus === 'function') {
      this.lastFocusedElement.focus();
    }
  }

  async submitDecision() {
    const s = store.getState();
    const actionType = document.querySelector('input[name="decision-choice"]:checked')?.value || 'CONFIRM_DEFICIENCY';
    const reason = document.getElementById('decision-remarks').value;
    const findingId = s.selectedFindingId;

    // Never commit to the audit chain against a made-up finding.
    if (!findingId) {
      window.appToast.show('Select a finding in the Evidence Studio before recording a decision.', 'warning');
      return;
    }
    if (actionType === 'DISMISS_FINDING' && reason.trim().length < 10) {
      window.appToast.show('A justification of at least 10 characters is required to dismiss a finding.', 'warning');
      return;
    }

    const submitBtn = document.getElementById('btn-modal-submit');
    if (submitBtn) submitBtn.disabled = true;
    try {
      const actorId = api.currentUser?.id || api.currentUser?.user_id || 'usr-officer-01';
      await api.recordReviewAction(findingId, actionType, reason, actorId, s.activeApplicationId);
      window.appToast.show(`Decision '${actionType}' committed to cryptographic audit ledger!`);
      this.closeDecisionModal();
    } catch (err) {
      window.appToast.show(`Failed to record decision: ${err.message}`, 'danger');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }
}

class AppRouter {
  constructor() {
    this.contentEl = document.getElementById('main-content');
    this.views = {
      'command-center': new CommandCenterView(this.contentEl),
      'queue': new ReviewerQueueView(this.contentEl),
      'preflight': new InstitutionPreflightView(this.contentEl),
      'case-file': new CaseFileView(this.contentEl),
      'studio': new EvidenceStudioView(this.contentEl),
      'verification': new VerificationLadderView(this.contentEl),
      'comparison': new ComparisonView(this.contentEl),
      'audit': new AuditLedgerView(this.contentEl)
    };
    this.currentView = null;
  }

  async init() {
    const roleSelect = document.getElementById('role-select');
    if (roleSelect) {
      roleSelect.disabled = true;
    }

    this.bindEvents();
    this.bindKeyboardShortcuts();

    const health = await this.checkBackendHealth();
    const demoModeEnabled = health?.data?.is_demo_mode === true;

    if (roleSelect) {
      roleSelect.disabled = !demoModeEnabled;
    }

    if (demoModeEnabled) {
      await this.initSession();
    } else {
      api.setSession(null, null);
    }

    this.navigate('command-center');
  }

  async initSession() {
    try {
      const user = await api.ensureSession('usr-officer-01');
      if (user) {
        const roleSelect = document.getElementById('role-select');
        if (roleSelect) {
          if (user.role === 'REVIEWER') roleSelect.value = 'reviewer';
          else if (user.role === 'INSTITUTION_USER') roleSelect.value = 'institution_user';
          else if (user.role === 'AUDITOR') roleSelect.value = 'auditor';
          else if (user.role === 'RULES_ADMIN') roleSelect.value = 'rules_admin';
        }
      }
    } catch (err) {
      console.warn('Session initialization:', err);
    }
  }

  async checkBackendHealth() {
    try {
      const res = await api.getHealth();
      const dot = document.getElementById('health-indicator-dot');
      const text = document.getElementById('health-indicator-text');

      if (res.data?.status === 'healthy') {
        dot.style.backgroundColor = '#22c55e';
        text.textContent = res.data?.is_demo_mode === false
          ? 'Backend: Operational (Demo disabled)'
          : 'Backend: Operational';
      }

      return res;
    } catch (_) {
      const dot = document.getElementById('health-indicator-dot');
      const text = document.getElementById('health-indicator-text');
      dot.style.backgroundColor = '#ef4444';
      text.textContent = 'Backend: Offline';
      return null;
    }
  }

  navigate(routeName) {
    if (!this.views[routeName]) return;

    store.setState({ currentRoute: routeName });

    // Update active tab styles
    const tabs = document.querySelectorAll('.nav-tab-btn');
    tabs.forEach(t => {
      if (t.dataset.route === routeName) {
        t.classList.add('active');
      } else {
        t.classList.remove('active');
      }
    });

    this.currentView = this.views[routeName];
    this.currentView.render();
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  openCase(applicationId) {
    store.setState({ activeApplicationId: applicationId });
    this.navigate('case-file');
  }

  bindEvents() {
    const tabs = document.querySelectorAll('.nav-tab-btn');
    tabs.forEach(tab => {
      tab.onclick = () => {
        this.navigate(tab.dataset.route);
      };
    });

    const roleSelect = document.getElementById('role-select');
    if (roleSelect) {
      roleSelect.onchange = async (e) => {
        if (roleSelect.disabled) return;

        const roleUserMap = {
          'reviewer': 'usr-officer-01',
          'institution_user': 'usr-inst-apex',
          'auditor': 'usr-auditor-01',
          'rules_admin': 'usr-admin-01'
        };
        const userId = roleUserMap[e.target.value] || 'usr-officer-01';
        try {
          const res = await api.createSession(userId);
          api.setSession(res.data.session_token, res.data.user);
          store.setState({ role: e.target.value });
          window.appToast.show(`Authenticated as: ${res.data.user.full_name}`);
        } catch (err) {
          window.appToast.show(`Session switch error: ${err.message}`, 'danger');
        }

        if (e.target.value === 'institution_user') {
          this.navigate('preflight');
        } else if (e.target.value === 'auditor') {
          this.navigate('audit');
        } else {
          this.navigate('queue');
        }
      };
    }

    // Modal submit & close bindings
    document.getElementById('btn-modal-cancel')?.addEventListener('click', () => window.appModal.closeDecisionModal());
    document.getElementById('btn-modal-submit')?.addEventListener('click', () => window.appModal.submitDecision());
  }

  bindKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      const inInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);

      if (e.key === 'Escape') {
        window.appModal.closeDecisionModal();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        this.navigate('queue');
        setTimeout(() => document.getElementById('queue-search')?.focus(), 100);
      } else if (!inInput && e.key.toLowerCase() === 'r' && (store.getState().currentRoute === 'studio' || store.getState().currentRoute === 'case-file')) {
        e.preventDefault();
        window.appModal.openDecisionModal();
      } else if (!inInput && store.getState().currentRoute === 'studio') {
        if (e.key.toLowerCase() === 'j' || e.key === 'ArrowDown') {
          e.preventDefault();
          this.views.studio.navigateFinding(1);
        } else if (e.key.toLowerCase() === 'k' || e.key === 'ArrowUp') {
          e.preventDefault();
          this.views.studio.navigateFinding(-1);
        } else if (e.key.toLowerCase() === 'p') {
          e.preventDefault();
          this.views.studio.setRightMode('pdf');
        } else if (e.key.toLowerCase() === 'g') {
          e.preventDefault();
          this.views.studio.setRightMode('graph');
        } else if (e.key.toLowerCase() === 't') {
          e.preventDefault();
          this.views.studio.toggleGraphSubMode();
        } else if (e.key === '+' || e.key === '=') {
          e.preventDefault();
          this.views.studio.setZoom(0.15);
        } else if (e.key === '-' || e.key === '_') {
          e.preventDefault();
          this.views.studio.setZoom(-0.15);
        } else if (e.key === '0') {
          e.preventDefault();
          this.views.studio.resetZoom();
        }
      }
    });
  }
}

// Global Singletons
window.appToast = new ToastManager();
window.appModal = new ModalManager();
window.appRouter = new AppRouter();

window.addEventListener('DOMContentLoaded', () => {
  window.appRouter.init();
});
