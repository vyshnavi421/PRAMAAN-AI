/**
 * PRAMAAN-AI Central State Store
 * Manages active role, selected application, current route, active findings, and review reports.
 */

class StateStore {
  constructor() {
    this.state = {
      role: 'reviewer', // 'reviewer', 'institution_user', 'rules_admin', 'auditor'
      currentRoute: 'command-center', // 'command-center', 'queue', 'preflight', 'case-file', 'studio', 'verification', 'comparison', 'audit'
      activeApplicationId: 'app-case-clean',
      activeApplicationData: null,
      activeReviewReport: null,
      selectedFindingId: null,
      activeGraphView: 'canvas', // 'canvas' or 'table'
      queueSearchQuery: '',
      queueCategoryFilter: 'ALL',
      queueSortColumn: 'status',
      queueSortDirection: 'asc',
      isReviewExecuting: false,
      lastLatencyMs: 0
    };
    this.listeners = [];
  }

  getState() {
    return this.state;
  }

  setState(partialState) {
    this.state = { ...this.state, ...partialState };
    this.notify();
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notify() {
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }
}

export const store = new StateStore();
