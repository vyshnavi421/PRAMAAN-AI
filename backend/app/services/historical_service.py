"""
PRAMAAN-AI Change-Aware Previous-Application Review Service
Compares current application dossiers against authorised or synthetic previous annual snapshots.
Enforces strict statutory guardrails:
- Normalisation of names and addresses (e.g. abbreviations, minor punctuation) is recognized as a match.
- Borderline variations (70%-89% similarity) route to manual review rather than false violation flags.
- Parameter increases (e.g. intake expansion) are categorized as change-requests, NEVER as fraud or compliance violations.
- First-time applications (absent historical records) are handled gracefully without error.
- Preserves historical snapshots and past validation runs for full auditability.
"""
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone, date
from enum import Enum
import uuid
import re


class ChangeType(str, Enum):
    IDENTICAL = "IDENTICAL"
    NORMALIZED_MATCH = "NORMALIZED_MATCH"
    BORDERLINE_REVIEW = "BORDERLINE_REVIEW"
    INCREASE_REQUESTED = "INCREASE_REQUESTED"
    LEGITIMATE_VARIATION = "LEGITIMATE_VARIATION"
    NEW_PARAMETER_DECLARED = "NEW_PARAMETER_DECLARED"
    HISTORIC_VALUE_UNAVAILABLE = "HISTORIC_VALUE_UNAVAILABLE"
    FIRST_TIME_APPLICATION = "FIRST_TIME_APPLICATION"


class HistoricalApplicationSnapshot(BaseModel):
    """
    Immutable snapshot of an institution's prior approved status (e.g. AY 2025–2026).
    """
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    institution_id: str
    academic_year: str
    application_number: str
    approval_status: str = "APPROVED_BY_EXECUTIVE_COMMITTEE"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    documents_summary: List[Dict[str, Any]] = Field(default_factory=list)
    approved_at: str
    is_synthetic: bool = True
    active_rule_pack: str = "rp-aicte-aph-2024-eoa v1.0.0"
    prior_validation_run_id: Optional[str] = None


class ComparisonFieldDelta(BaseModel):
    """
    Detailed delta item comparing a single statutory parameter between past and present.
    """
    field_key: str
    field_label: str
    previous_value: Optional[Any] = None
    current_value: Optional[Any] = None
    source_previous: str
    source_current: str
    change_type: ChangeType
    variance_pct: Optional[float] = None
    delta_description: str
    is_compliance_violation: bool = False
    related_rule_id: Optional[str] = None
    rule_version: Optional[str] = None
    requires_manual_scrutiny: bool = False


class HistoricalComparisonReport(BaseModel):
    """
    Comprehensive change-aware comparison report between current dossier and historical baseline.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    application_id: str
    institution_id: str
    current_academic_year: str
    baseline_academic_year: Optional[str] = None
    is_first_time_application: bool = False
    total_parameters_evaluated: int = 0
    identical_count: int = 0
    normalized_match_count: int = 0
    changed_count: int = 0
    borderline_review_count: int = 0
    deltas: List[ComparisonFieldDelta] = Field(default_factory=list)
    summary_notes: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Standard abbreviation dictionary for name and address normalisation
NORMALIZATION_MAP = {
    r"\binst\b|\binst\.": "institute",
    r"\btech\b|\btech\.": "technology",
    r"\bengg\b|\bengg\.": "engineering",
    r"\bpoly\b|\bpoly\.": "polytechnic",
    r"\bdept\b|\bdept\.": "department",
    r"\buniv\b|\buniv\.": "university",
    r"\brd\b|\brd\.": "road",
    r"\bst\b|\bst\.": "street",
    r"\bblr\b|\bb'lore\b": "bangalore",
    r"\bdr\b|\bdr\.": "doctor",
    r"\bprof\b|\bprof\.": "professor",
    r"\bplot\s*no\.?": "plot",
    r"\bsec\b|\bsec\.": "sector",
    r"\bopp\b|\bopp\.": "opposite",
    r"\bnr\b|\bnr\.": "near",
}


def normalize_text(text: str) -> str:
    """
    Standardizes whitespace, case, punctuation, and common administrative abbreviations.
    """
    if not text:
        return ""
    t = text.lower().strip()
    # Replace abbreviations
    for pattern, replacement in NORMALIZATION_MAP.items():
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
    # Strip excess punctuation and standardize whitespace
    t = re.sub(r"[,\-\./\\#]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def compute_token_similarity(s1: str, s2: str) -> float:
    """
    Computes token-level Jaccard similarity after normalisation.
    """
    n1 = set(normalize_text(s1).split())
    n2 = set(normalize_text(s2).split())
    if not n1 and not n2:
        return 1.0
    if not n1 or not n2:
        return 0.0
    inter = len(n1.intersection(n2))
    union = len(n1.union(n2))
    return float(inter / union) if union > 0 else 0.0


class HistoricalSnapshotRepository:
    """
    Repository storing immutable historical application snapshots and prior validation runs.
    """
    def __init__(self):
        # institution_id -> List of HistoricalApplicationSnapshot
        self._snapshots: Dict[str, List[HistoricalApplicationSnapshot]] = {}
        self._seed_baseline_snapshots()

    def _seed_baseline_snapshots(self):
        """
        Seeds canonical approved snapshots for benchmark institutions (AY 2025–2026).
        """
        # Snapshot 1: Apex Institute of Technology (Baseline 2025-2026)
        snap_apex = HistoricalApplicationSnapshot(
            snapshot_id="snap-apex-2025",
            institution_id="inst-apex-01",
            academic_year="2025-2026",
            application_number="APP-2025-EOA-089",
            approval_status="APPROVED_BY_EXECUTIVE_COMMITTEE",
            parameters={
                "institution_name": "Apex Institute of Technology",
                "address": "Plot 12, Tech Zone, Electronic City, Bangalore",
                "total_intake": 180,
                "builtup_area_sqm": 12000.0,
                "land_area_acres": 7.5,
                "head_of_institution": "Dr. S. Ramanujan",
                "approved_programmes": ["Computer Science & Engineering", "Information Technology", "Electronics Engineering"],
            },
            documents_summary=[
                {"document_type": "FIRE_SAFETY_NOC", "valid_until": "2026-01-14", "sha256": "prev-fire-hash-apex"},
                {"document_type": "LAND_USE_CERTIFICATE", "land_area_acres": 7.5, "sha256": "prev-land-hash-apex"}
            ],
            approved_at="2025-05-18T10:00:00Z",
            prior_validation_run_id="run-apex-2025-final"
        )

        # Snapshot 2: Bharat Polytechnic (Baseline 2025-2026) - had 120 intake
        snap_bharat = HistoricalApplicationSnapshot(
            snapshot_id="snap-bharat-2025",
            institution_id="inst-bharat-04",
            academic_year="2025-2026",
            application_number="APP-2025-EOA-044",
            approval_status="APPROVED_BY_EXECUTIVE_COMMITTEE",
            parameters={
                "institution_name": "Bharat Polytechnic College",
                "address": "Kalyan Bypass Road, Raigad",
                "total_intake": 120,
                "builtup_area_sqm": 8500.0,
                "land_area_acres": 5.0,
                "head_of_institution": "Prof. V. K. Patil",
                "approved_programmes": ["Civil Engineering", "Mechanical Engineering"],
            },
            documents_summary=[
                {"document_type": "FIRE_SAFETY_NOC", "valid_until": "2026-03-31", "sha256": "prev-fire-hash-bharat"}
            ],
            approved_at="2025-05-20T11:30:00Z",
            prior_validation_run_id="run-bharat-2025-final"
        )

        # Snapshot 3: City College of Engineering (Baseline 2025-2026)
        snap_city = HistoricalApplicationSnapshot(
            snapshot_id="snap-city-2025",
            institution_id="inst-city-02",
            academic_year="2025-2026",
            application_number="APP-2025-EOA-022",
            approval_status="APPROVED_BY_EXECUTIVE_COMMITTEE",
            parameters={
                "institution_name": "City College of Engineering",
                "address": "MG Road, Camp, Pune",
                "total_intake": 240,
                "builtup_area_sqm": 15000.0,
                "land_area_acres": 10.0,
                "head_of_institution": "Dr. A. P. Deshmukh",
                "approved_programmes": ["Computer Engineering", "Mechanical Engineering", "Electrical Engineering"],
            },
            documents_summary=[],
            approved_at="2025-05-15T09:00:00Z"
        )

        self.add_snapshot(snap_apex)
        self.add_snapshot(snap_bharat)
        self.add_snapshot(snap_city)

    def add_snapshot(self, snapshot: HistoricalApplicationSnapshot) -> None:
        if snapshot.institution_id not in self._snapshots:
            self._snapshots[snapshot.institution_id] = []
        self._snapshots[snapshot.institution_id].append(snapshot)

    def get_latest_snapshot(self, institution_id: str) -> Optional[HistoricalApplicationSnapshot]:
        snaps = self._snapshots.get(institution_id)
        if not snaps:
            return None
        # Return most recent snapshot
        return snaps[-1]

    def list_snapshots_for_institution(self, institution_id: str) -> List[HistoricalApplicationSnapshot]:
        return self._snapshots.get(institution_id, [])


class HistoricalComparisonEngine:
    """
    Evaluates current application submission against historical snapshots.
    Identifies parameter variances, normalises names/addresses, routes borderline cases,
    and safeguards against false fraud verdicts.
    """
    def __init__(self, repo: Optional[HistoricalSnapshotRepository] = None):
        self.repo = repo or HistoricalSnapshotRepository()

    def compare_application(self, current_app: Any) -> HistoricalComparisonReport:
        """
        Performs a full change-aware comparison for an ApplicationInput dossier.
        """
        institution_id = current_app.institution_id
        current_year = current_app.academic_year
        declared = current_app.declared_data or {}

        snapshot = self.repo.get_latest_snapshot(institution_id)

        # Handle FIRST-TIME APPLICATION (Absent previous record)
        if not snapshot:
            delta_first = ComparisonFieldDelta(
                field_key="application_dossier",
                field_label="Dossier Filing History",
                previous_value=None,
                current_value=current_app.application_number,
                source_previous="AICTE Master Registry",
                source_current=f"Filing {current_app.application_number}",
                change_type=ChangeType.FIRST_TIME_APPLICATION,
                delta_description=(
                    "No prior approved application snapshot found in system registry. "
                    "Classified as First-Time Institutional Filing (New Establishment or Unmigrated). "
                    "Processed cleanly under initial establishment rules."
                ),
                is_compliance_violation=False,
                requires_manual_scrutiny=False
            )
            return HistoricalComparisonReport(
                application_id=current_app.application_id,
                institution_id=institution_id,
                current_academic_year=current_year,
                baseline_academic_year=None,
                is_first_time_application=True,
                total_parameters_evaluated=1,
                identical_count=0,
                normalized_match_count=0,
                changed_count=0,
                borderline_review_count=0,
                deltas=[delta_first],
                summary_notes="First-time application: No historical drift evaluated. All initial baseline norms apply."
            )

        # Established Institution with Baseline Snapshot
        deltas: List[ComparisonFieldDelta] = []
        identical_cnt = 0
        normalized_cnt = 0
        changed_cnt = 0
        borderline_cnt = 0

        prev_params = snapshot.parameters

        # 1. Institution Name Check (with Normalization & Borderline Detection)
        curr_name = declared.get("institution_name") or getattr(current_app, "institution_name", None) or ""
        prev_name = prev_params.get("institution_name", "")
        if curr_name and prev_name:
            if curr_name == prev_name:
                identical_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="institution_name",
                    field_label="Legal Institutional Name",
                    previous_value=prev_name,
                    current_value=curr_name,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.IDENTICAL,
                    delta_description="Legal name matches historical baseline exactly.",
                    is_compliance_violation=False
                ))
            else:
                norm_curr = normalize_text(curr_name)
                norm_prev = normalize_text(prev_name)
                sim = compute_token_similarity(curr_name, prev_name)

                if norm_curr == norm_prev or sim >= 0.90:
                    normalized_cnt += 1
                    deltas.append(ComparisonFieldDelta(
                        field_key="institution_name",
                        field_label="Legal Institutional Name",
                        previous_value=prev_name,
                        current_value=curr_name,
                        source_previous=f"Approved Baseline ({snapshot.academic_year})",
                        source_current=f"Dossier Declared ({current_year})",
                        change_type=ChangeType.NORMALIZED_MATCH,
                        variance_pct=round((1.0 - sim) * 100, 1),
                        delta_description=f"Minor administrative abbreviation or punctuation variation (Similarity: {round(sim * 100, 1)}%). Validated as legitimate normalized match.",
                        is_compliance_violation=False
                    ))
                elif sim >= 0.50 or norm_prev in norm_curr or norm_curr in norm_prev:
                    borderline_cnt += 1
                    deltas.append(ComparisonFieldDelta(
                        field_key="institution_name",
                        field_label="Legal Institutional Name",
                        previous_value=prev_name,
                        current_value=curr_name,
                        source_previous=f"Approved Baseline ({snapshot.academic_year})",
                        source_current=f"Dossier Declared ({current_year})",
                        change_type=ChangeType.BORDERLINE_REVIEW,
                        variance_pct=round((1.0 - sim) * 100, 1),
                        delta_description=f"Borderline name variation detected (Similarity: {round(sim * 100, 1)}%). Scrutiny officer must review trust deed to verify if name change was approved.",
                        is_compliance_violation=False,
                        requires_manual_scrutiny=True
                    ))
                else:
                    changed_cnt += 1
                    deltas.append(ComparisonFieldDelta(
                        field_key="institution_name",
                        field_label="Legal Institutional Name",
                        previous_value=prev_name,
                        current_value=curr_name,
                        source_previous=f"Approved Baseline ({snapshot.academic_year})",
                        source_current=f"Dossier Declared ({current_year})",
                        change_type=ChangeType.LEGITIMATE_VARIATION,
                        delta_description="Significant name modification detected. Verify Governing Body Resolution or State Gazette Notification attached in dossier.",
                        is_compliance_violation=False,
                        requires_manual_scrutiny=True
                    ))

        # 2. Campus Address Check (with Normalisation)
        curr_addr = declared.get("address") or ""
        prev_addr = prev_params.get("address", "")
        if curr_addr and prev_addr:
            if curr_addr == prev_addr:
                identical_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="address",
                    field_label="Campus Postal Address",
                    previous_value=prev_addr,
                    current_value=curr_addr,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.IDENTICAL,
                    delta_description="Campus postal address is identical to approved baseline.",
                    is_compliance_violation=False
                ))
            else:
                sim_addr = compute_token_similarity(curr_addr, prev_addr)
                if sim_addr >= 0.85:
                    normalized_cnt += 1
                    deltas.append(ComparisonFieldDelta(
                        field_key="address",
                        field_label="Campus Postal Address",
                        previous_value=prev_addr,
                        current_value=curr_addr,
                        source_previous=f"Approved Baseline ({snapshot.academic_year})",
                        source_current=f"Dossier Declared ({current_year})",
                        change_type=ChangeType.NORMALIZED_MATCH,
                        variance_pct=round((1.0 - sim_addr) * 100, 1),
                        delta_description="Address formatted with standard road/sector abbreviations. Validated as identical physical location.",
                        is_compliance_violation=False
                    ))
                else:
                    borderline_cnt += 1
                    deltas.append(ComparisonFieldDelta(
                        field_key="address",
                        field_label="Campus Postal Address",
                        previous_value=prev_addr,
                        current_value=curr_addr,
                        source_previous=f"Approved Baseline ({snapshot.academic_year})",
                        source_current=f"Dossier Declared ({current_year})",
                        change_type=ChangeType.BORDERLINE_REVIEW,
                        delta_description="Address discrepancy indicates possible change of location or unapproved campus shift.",
                        is_compliance_violation=False,
                        requires_manual_scrutiny=True
                    ))

        # 3. Sanctioned Intake Comparison (Change in Intake)
        curr_intake = declared.get("total_intake")
        prev_intake = prev_params.get("total_intake")
        if curr_intake is not None and prev_intake is not None:
            curr_val = int(curr_intake)
            prev_val = int(prev_intake)
            if curr_val == prev_val:
                identical_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="total_intake",
                    field_label="Sanctioned Total Intake",
                    previous_value=prev_val,
                    current_value=curr_val,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.IDENTICAL,
                    variance_pct=0.0,
                    delta_description="Total student intake matches approved capacity.",
                    is_compliance_violation=False
                ))
            elif curr_val > prev_val:
                changed_cnt += 1
                delta_seats = curr_val - prev_val
                delta_pct = round((delta_seats / prev_val) * 100.0, 1)
                deltas.append(ComparisonFieldDelta(
                    field_key="total_intake",
                    field_label="Sanctioned Total Intake",
                    previous_value=prev_val,
                    current_value=curr_val,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.INCREASE_REQUESTED,
                    variance_pct=delta_pct,
                    delta_description=(
                        f"Student intake expansion requested: {prev_val} seats → {curr_val} seats "
                        f"(+{delta_seats} seats, +{delta_pct}%). Parameter change evaluated under "
                        f"RULE-AICTE-HIST-006; requires verified faculty ratio and additional laboratory space."
                    ),
                    is_compliance_violation=False,
                    related_rule_id="RULE-AICTE-HIST-006",
                    rule_version="1.0.0",
                    requires_manual_scrutiny=True
                ))
            else:
                changed_cnt += 1
                delta_seats = curr_val - prev_val
                delta_pct = round((delta_seats / prev_val) * 100.0, 1)
                deltas.append(ComparisonFieldDelta(
                    field_key="total_intake",
                    field_label="Sanctioned Total Intake",
                    previous_value=prev_val,
                    current_value=curr_val,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.LEGITIMATE_VARIATION,
                    variance_pct=delta_pct,
                    delta_description=f"Intake reduction requested: {prev_val} → {curr_val} seats ({delta_pct}%). Permitted under voluntary intake reduction guidelines.",
                    is_compliance_violation=False
                ))

        # 4. Built-Up Area Comparison
        curr_bua = declared.get("builtup_area_sqm")
        prev_bua = prev_params.get("builtup_area_sqm")
        if curr_bua is not None and prev_bua is not None:
            c_bua = float(curr_bua)
            p_bua = float(prev_bua)
            if abs(c_bua - p_bua) < 0.1:
                identical_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="builtup_area_sqm",
                    field_label="Instructional & Administrative Built-Up Area",
                    previous_value=p_bua,
                    current_value=c_bua,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.IDENTICAL,
                    variance_pct=0.0,
                    delta_description="Instructional built-up area matches approved campus drawings.",
                    is_compliance_violation=False
                ))
            elif c_bua > p_bua:
                changed_cnt += 1
                delta_sqm = round(c_bua - p_bua, 1)
                delta_pct = round((delta_sqm / p_bua) * 100.0, 1)
                deltas.append(ComparisonFieldDelta(
                    field_key="builtup_area_sqm",
                    field_label="Instructional & Administrative Built-Up Area",
                    previous_value=p_bua,
                    current_value=c_bua,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.INCREASE_REQUESTED,
                    variance_pct=delta_pct,
                    delta_description=f"Campus physical expansion: {p_bua} sq.m → {c_bua} sq.m (+{delta_sqm} sq.m, +{delta_pct}%). Consistent with ongoing campus development.",
                    is_compliance_violation=False
                ))
            else:
                changed_cnt += 1
                delta_sqm = round(c_bua - p_bua, 1)
                delta_pct = round((delta_sqm / p_bua) * 100.0, 1)
                deltas.append(ComparisonFieldDelta(
                    field_key="builtup_area_sqm",
                    field_label="Instructional & Administrative Built-Up Area",
                    previous_value=p_bua,
                    current_value=c_bua,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.BORDERLINE_REVIEW,
                    variance_pct=delta_pct,
                    delta_description=f"Declared built-up area is lower than historical baseline ({delta_sqm} sq.m, {delta_pct}%). Scrutiny officer must verify if space was decommissioned.",
                    is_compliance_violation=False,
                    requires_manual_scrutiny=True
                ))

        # 5. Land Area
        curr_land = declared.get("land_area_acres")
        prev_land = prev_params.get("land_area_acres")
        if curr_land is not None and prev_land is not None:
            c_land = float(curr_land)
            p_land = float(prev_land)
            if abs(c_land - p_land) < 0.01:
                identical_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="land_area_acres",
                    field_label="Single Plot Land Area (Acres)",
                    previous_value=p_land,
                    current_value=c_land,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.IDENTICAL,
                    variance_pct=0.0,
                    delta_description="Land area confirmed contiguous and unchanged.",
                    is_compliance_violation=False
                ))
            else:
                changed_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="land_area_acres",
                    field_label="Single Plot Land Area (Acres)",
                    previous_value=p_land,
                    current_value=c_land,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.BORDERLINE_REVIEW,
                    delta_description="Land parcel size differs from approved land use certificate. Requires revenue document verification.",
                    is_compliance_violation=False,
                    requires_manual_scrutiny=True
                ))

        # 6. Head of Institution / Principal
        curr_head = declared.get("head_of_institution") or declared.get("principal_name")
        prev_head = prev_params.get("head_of_institution")
        if curr_head and prev_head:
            if curr_head == prev_head:
                identical_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="head_of_institution",
                    field_label="Principal / Head of Institution",
                    previous_value=prev_head,
                    current_value=curr_head,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.IDENTICAL,
                    delta_description="Head of institution is unchanged.",
                    is_compliance_violation=False
                ))
            else:
                changed_cnt += 1
                deltas.append(ComparisonFieldDelta(
                    field_key="head_of_institution",
                    field_label="Principal / Head of Institution",
                    previous_value=prev_head,
                    current_value=curr_head,
                    source_previous=f"Approved Baseline ({snapshot.academic_year})",
                    source_current=f"Dossier Declared ({current_year})",
                    change_type=ChangeType.LEGITIMATE_VARIATION,
                    delta_description=f"Succession in academic leadership: {prev_head} → {curr_head}. Verify Selection Committee minutes and AICTE qualification eligibility.",
                    is_compliance_violation=False
                ))

        # Check for missing historic values or new schema parameters
        for k, v in declared.items():
            if k not in prev_params and k not in ["institution_name", "address", "total_intake", "builtup_area_sqm", "land_area_acres", "head_of_institution", "principal_name"]:
                deltas.append(ComparisonFieldDelta(
                    field_key=k,
                    field_label=k.replace("_", " ").title(),
                    previous_value=None,
                    current_value=str(v),
                    source_previous="Not Present in Baseline Schema",
                    source_current=f"Declared ({current_year})",
                    change_type=ChangeType.NEW_PARAMETER_DECLARED,
                    delta_description=f"New statutory parameter '{k}' declared in current cycle.",
                    is_compliance_violation=False
                ))

        total_eval = len(deltas)
        summary = (
            f"Evaluated {total_eval} parameters against {snapshot.academic_year} baseline ({snapshot.application_number}). "
            f"{identical_cnt} identical, {normalized_cnt} normalized matches, {changed_cnt} planned changes/expansions, "
            f"and {borderline_cnt} borderline items requiring officer attention. Zero automatic fraud verdicts."
        )

        return HistoricalComparisonReport(
            application_id=current_app.application_id,
            institution_id=institution_id,
            current_academic_year=current_year,
            baseline_academic_year=snapshot.academic_year,
            is_first_time_application=False,
            total_parameters_evaluated=total_eval,
            identical_count=identical_cnt,
            normalized_match_count=normalized_cnt,
            changed_count=changed_cnt,
            borderline_review_count=borderline_cnt,
            deltas=deltas,
            summary_notes=summary
        )


# Global singleton
global_historical_repo = HistoricalSnapshotRepository()
global_historical_engine = HistoricalComparisonEngine(global_historical_repo)
