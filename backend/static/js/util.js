/**
 * PRAMAAN-AI shared UI helpers.
 * escapeHtml() must wrap every server- or user-controlled string that is
 * interpolated into an innerHTML template (filenames, institution names,
 * error messages, rule text...) to prevent stored/reflected XSS.
 */
const ENTITY_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' };

export function esc(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>"'`]/g, (ch) => ENTITY_MAP[ch]);
}
