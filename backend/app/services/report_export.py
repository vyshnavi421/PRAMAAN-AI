"""
PRAMAAN-AI Scrutiny Report & Draft Deficiency Letter generator.

Deterministic, template-based (no LLM): every sentence is assembled from rule output that
already carries rule ID/version, clause citation and evidence. All dynamic text is
HTML-escaped. Outputs are decision-support DRAFTS that a human officer must review and issue.
"""
from datetime import datetime, timezone
from html import escape
from typing import List

from app.services.review_orchestrator import ReviewReport
from app.models.validation import Finding
from app.models.enums import FindingStatus

DISCLAIMER = (
    "DEMO / SIMULATED — PRAMAAN-AI is a decision-support prototype for SIH26261, not an official AICTE system. "
    "Findings are advisory pre-scrutiny signals. They are not determinations of fraud, and final approval, "
    "rejection and inspection decisions rest solely with the competent AICTE authority."
)

_CSS = """
body{font:14px/1.5 system-ui,Segoe UI,Arial,sans-serif;color:#1a2230;max-width:880px;margin:2rem auto;padding:0 1rem}
h1{font-size:1.5rem;margin:0}h2{font-size:1.1rem;border-bottom:2px solid #d9e0ec;padding-bottom:.25rem;margin-top:2rem}
.banner{background:#fff4d6;border:1px solid #e6c15a;padding:.6rem .8rem;border-radius:6px;font-size:.85rem}
table{border-collapse:collapse;width:100%;margin:.5rem 0}td,th{border:1px solid #d9e0ec;padding:.4rem .55rem;text-align:left;vertical-align:top;font-size:.85rem}
th{background:#f1f4fa}.pill{display:inline-block;padding:.05rem .5rem;border-radius:999px;font-size:.75rem;font-weight:600;background:#e8edf7}
.DEFICIENCY{background:#ffe0e0}.ANOMALY_SIGNAL{background:#ffeccc}.INCONCLUSIVE{background:#e4e4f7}.COMPLIANT{background:#dcf5e3}
.finding{border:1px solid #d9e0ec;border-radius:8px;padding:.7rem .9rem;margin:.7rem 0}.muted{color:#5b6779;font-size:.8rem}
@media print{.banner{break-inside:avoid}.finding{break-inside:avoid}}
"""


def _e(value) -> str:
    return escape("" if value is None else str(value), quote=True)


def _evidence_rows(finding: Finding) -> str:
    if not finding.evidence:
        return '<p class="muted">No document evidence attached (evidence unavailable for this check).</p>'
    rows = []
    for ev in finding.evidence:
        loc = f"p.{ev.page_number}" if ev.page_number else "—"
        if ev.bounding_box:
            loc += f" @ {[round(x, 2) for x in ev.bounding_box]}"
        rows.append(
            f"<tr><td>{_e(ev.document_type)}<br><span class='muted'>{_e(ev.document_id)}</span></td>"
            f"<td>{_e(ev.field_key)}</td><td>{_e(ev.extracted_value)}</td>"
            f"<td>{_e(ev.comparison_value)}<br><span class='muted'>{_e(ev.comparison_source)}</span></td><td>{_e(loc)}</td></tr>"
        )
    return ("<table><tr><th>Source document</th><th>Field</th><th>Extracted value</th><th>Compared with</th>"
            "<th>Location</th></tr>" + "".join(rows) + "</table>")


def _finding_block(f: Finding) -> str:
    return (
        f"<div class='finding'><span class='pill {_e(f.status.value)}'>{_e(f.status.value)}</span> "
        f"<strong>{_e(f.rule_name)}</strong> <span class='muted'>({_e(f.rule_id)} v{_e(f.rule_version)})</span>"
        f"<p>{_e(f.reason)}</p><p class='muted'>Basis: {_e(f.clause_citation)}</p>"
        f"{_evidence_rows(f)}<p><strong>Recommended next action:</strong> {_e(f.recommended_action)}</p></div>"
    )


def _actionable(report: ReviewReport) -> List[Finding]:
    order = {FindingStatus.DEFICIENCY: 0, FindingStatus.ANOMALY_SIGNAL: 1}
    return sorted(report.findings, key=lambda f: order.get(f.status, 2))


def build_scrutiny_report_html(report: ReviewReport, institution_name: str) -> str:
    cov = report.coverage_audit
    findings = _actionable(report)
    verifs = "".join(
        f"<tr><td>{_e(v.document_type.value)}<br><span class='muted'>{_e(v.document_id)}</span></td>"
        f"<td>{_e(v.adapter_name)} <span class='muted'>(simulated)</span></td>"
        f"<td><span class='pill'>{_e(v.status.value)}</span></td>"
        f"<td class='muted'>{_e(v.scope_limitations)}</td></tr>"
        for v in report.source_verifications
    ) or "<tr><td colspan='4'>No source verification attempts recorded.</td></tr>"
    inconclusive = "".join(_finding_block(f) for f in report.inconclusive_checks)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Pre-Scrutiny Report — {_e(report.application_number)}</title><style>{_CSS}</style></head><body>
<div class="banner"><strong>{_e(DISCLAIMER)}</strong></div>
<h1>Pre-Scrutiny Report</h1>
<p>{_e(institution_name)} · {_e(report.application_number)} · {_e(report.category)} · AY {_e(report.academic_year)}</p>
<p class="muted">Review ID {_e(report.review_id)} · Rule pack {_e(report.rule_pack_id)} v{_e(report.rule_pack_version)} ·
Executed {_e(report.executed_at.isoformat())} · Input snapshot SHA-256 {_e(report.input_snapshot_hash)}</p>
<h2>Summary</h2>
<table><tr><th>Review status</th><th>Planned checks</th><th>Coverage</th><th>Deficiencies</th><th>Anomaly signals</th><th>Inconclusive</th></tr>
<tr><td>{_e(report.review_status)}</td><td>{_e(cov.total_planned)}</td><td>{_e(cov.coverage_percentage)}% ({_e(cov.audit_verdict)})</td>
<td>{_e(report.summary.get('deficiencies', 0))}</td><td>{_e(report.summary.get('anomalies', 0))}</td><td>{_e(report.summary.get('inconclusive', 0))}</td></tr></table>
<h2>Findings requiring officer attention ({len(findings)})</h2>
{''.join(_finding_block(f) for f in findings) or '<p>No deficiencies or anomaly signals were raised by the configured rules.</p>'}
<h2>Inconclusive checks — manual review needed ({len(report.inconclusive_checks)})</h2>
{inconclusive or '<p>None.</p>'}
<h2>Issuing-authority verification (simulated)</h2>
<table><tr><th>Document</th><th>Adapter</th><th>Status</th><th>What this does not establish</th></tr>{verifs}</table>
<h2>Passed checks</h2><p>{len(report.successful_checks)} checks passed; {len(report.not_applicable_checks)} not applicable.</p>
<p class="muted">Generated {_e(datetime.now(timezone.utc).isoformat())}. Use your browser's Print → Save as PDF to archive.</p>
</body></html>"""


def build_deficiency_letter_text(report: ReviewReport, institution_name: str, officer_name: str) -> str:
    items = [f for f in report.findings if f.status == FindingStatus.DEFICIENCY]
    items += list(report.inconclusive_checks)
    lines = [
        "DRAFT — NOT ISSUED. Requires review and approval by the scrutiny officer before sending.",
        "DEMO / SIMULATED (SIH26261 prototype)",
        "",
        f"To: The Head of Institution, {institution_name}",
        f"Re: Application {report.application_number} ({report.category}), Academic Year {report.academic_year}",
        f"Pre-scrutiny reference: {report.review_id}",
        "",
        "Sir/Madam,",
        "",
    ]
    if not items:
        lines += ["Pre-scrutiny of the documents submitted has not identified any deficiency requiring clarification.",
                  "This communication is not a decision on your application."]
    else:
        lines += ["Pre-scrutiny of the submitted documents indicates that the following points need your clarification "
                  "or supporting documents:", ""]
        for i, f in enumerate(items, 1):
            lines.append(f"{i}. {f.rule_name} [{f.clause_citation}]")
            lines.append(f"   Observation: {f.reason}")
            lines.append(f"   Requested action: {f.recommended_action}")
            lines.append("")
    lines += [
        "These observations are preliminary and generated with automated decision support; they are not a finding of "
        "misconduct and do not constitute approval or rejection. Please respond with clarifications or documents "
        "through the portal within the period notified by AICTE.",
        "",
        f"Scrutiny Officer: {officer_name}",
    ]
    return "\n".join(lines)
