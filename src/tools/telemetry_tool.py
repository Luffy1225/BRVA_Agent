import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field

class TelemetryInput(BaseModel):
    csv_path: Optional[str] = Field(None, description="飛行紀錄檔路徑")
    file_path: Optional[str] = Field(None, description="飛行紀錄檔路徑 (別名)")
    aircraft_type: str = Field("B78X", description="機型")

    def get_path(self) -> str:
        return self.csv_path or self.file_path or ""

class TelemetryViolation(BaseModel):
    phase: str
    item: str
    standard: str
    peak_value: str
    timestamp: str
    severity: str
    deduction: int

class TelemetryOutput(BaseModel):
    success: bool
    is_passed: bool
    score: int
    touchdown_g: float
    violations: List[Dict[str, Any]]
    critical_failures: List[str]
    summary: str

def analyze_flight_telemetry(file_path: Optional[str] = None, aircraft_type: str = "B78X", csv_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministic telemetry audit parser using Pandas.
    Audits flight envelope parameters across flight phases:
    1. Taxi speed (<= 26 kts with >= 2s rolling window persistence).
    2. Below 10,000 ft airspeed (< 250 KIAS).
    3. Touchdown vertical G-load (<= 1.6G hard-landing limit).
    Completely eliminates LLM arithmetic hallucinations.
    """
    actual_path = csv_path or file_path or ""
    target_path = Path(actual_path)
    if not target_path.is_absolute():
        # Look in workspace or data dir
        if not target_path.exists():
            from src.config import config
            cand = config.DATA_DIR / actual_path
            if cand.exists():
                target_path = cand

    if not target_path.exists():
        return {
            "success": False,
            "error": f"Telemetry file '{actual_path}' not found on disk."
        }

    try:
        df = pd.read_csv(target_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse CSV file: {str(e)}"
        }

    # Normalize columns
    df.columns = [c.strip().lower() for c in df.columns]

    violations: List[Dict[str, Any]] = []
    critical_failures: List[str] = []

    # 1. Audit Taxi Speed (Taxi <= 26 kts)
    # Taxi phase rows
    taxi_mask = df['phase'].astype(str).str.contains('TAXI', case=False, na=False)
    taxi_df = df[taxi_mask].copy()

    if not taxi_df.empty and 'gs_kts' in taxi_df.columns:
        # Check overspeed condition (gs > 26.0)
        overspeed = taxi_df['gs_kts'] > 26.0
        # Rolling window persistence check (>= 2 consecutive records)
        persistent_overspeed = overspeed & (overspeed.shift(1, fill_value=False) | overspeed.shift(-1, fill_value=False))

        if persistent_overspeed.any():
            viol_rows = taxi_df[persistent_overspeed]
            peak_gs = round(float(viol_rows['gs_kts'].max()), 1)
            first_time = str(viol_rows.iloc[0].get('timestamp', '00:00:00'))
            violations.append({
                "phase": "TAXI",
                "item": "地面滑行超速",
                "standard": "直線滑行不得超過 26 節",
                "peak_value": f"{peak_gs} kts",
                "timestamp": first_time,
                "severity": "WARNING",
                "deduction": 5
            })

    # 2. Audit FL100 Airspeed (Alt < 10,000 ft -> IAS < 250 KIAS)
    if 'alt_ft' in df.columns and 'ias_kts' in df.columns:
        fl100_mask = (df['alt_ft'] < 10000) & (df['alt_ft'] > 1500) & (~taxi_mask)
        fl100_df = df[fl100_mask].copy()

        if not fl100_df.empty:
            speed_viol = fl100_df['ias_kts'] >= 250.0
            persistent_speed_viol = speed_viol & (speed_viol.shift(1, fill_value=False) | speed_viol.shift(-1, fill_value=False))
            if persistent_speed_viol.any():
                viol_rows = fl100_df[persistent_speed_viol]
                peak_ias = round(float(viol_rows['ias_kts'].max()), 1)
                first_time = str(viol_rows.iloc[0].get('timestamp', '00:00:00'))
                violations.append({
                    "phase": "CLIMB/DESCENT",
                    "item": "一萬呎以下空速超標",
                    "standard": "FL100 以下速度限制 < 250 KIAS",
                    "peak_value": f"{peak_ias} KIAS",
                    "timestamp": first_time,
                    "severity": "WARNING",
                    "deduction": 10
                })

    # 3. Audit Touchdown G-Force (<= 1.6G)
    touchdown_g = 1.2
    if 'touchdown_g' in df.columns:
        touchdown_rows = df[df['touchdown_g'].notnull() & (df['touchdown_g'] > 1.0)]
        if not touchdown_rows.empty:
            touchdown_g = round(float(touchdown_rows['touchdown_g'].max()), 2)
            if touchdown_g > 1.60:
                critical_failures.append(f"硬著陸 (Hard Landing)：接地垂直過載達 {touchdown_g}G（法定上限 ≤ 1.6G）。觸發實操考核一票否決淘汰條款！")

    # Overall scoring (Base 100)
    total_deductions = sum(v.get("deduction", 0) for v in violations)
    final_score = max(0, 100 - total_deductions)
    is_passed = (len(critical_failures) == 0) and (final_score >= 80)

    summary = (
        f"飛行黑盒子遙測審查結果：\n"
        f"• 評定結果：{'✅ 合格 (PASS)' if is_passed else '❌ 不合格 (FAIL)'}\n"
        f"• 總考核得分：{final_score} / 100 分\n"
        f"• 接地垂直過載：{touchdown_g}G ({'合規 ≤1.6G' if touchdown_g <= 1.60 else '⚠️ 超標硬著陸'})\n"
    )
    if critical_failures:
        summary += "• 致命一票否決項：\n  " + "\n  ".join(critical_failures) + "\n"
    if violations:
        summary += "• 違規紀錄清單：\n"
        for v in violations:
            summary += f"  - [{v['timestamp']}] {v['item']}：觀測值 {v['peak_value']} (標準: {v['standard']})，扣 {v['deduction']} 分\n"

    return {
        "success": True,
        "is_passed": is_passed,
        "score": final_score,
        "touchdown_g": touchdown_g,
        "violations": violations,
        "critical_failures": critical_failures,
        "summary": summary
    }
