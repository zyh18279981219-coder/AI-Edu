from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Iterable

from DatabaseModule.store import get_database_store

STAGE_ORDER = ("engagement", "exploration", "explanation", "elaboration", "evaluation")


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return min(100.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return default


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_payload(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _effectiveness_level(score: float | None, evidence_status: str = "process_only") -> str:
    if evidence_status == "insufficient_evidence":
        return "依据不足"
    if score is None:
        return "待计算"
    if score >= 80:
        return "引导有效"
    if score >= 60:
        return "基本有效"
    if score >= 40:
        return "效果一般"
    return "效果较弱"


def _student_feedback(level: str, evidence_status: str) -> str:
    if evidence_status == "insufficient_evidence":
        return "本次 5E 引导已记录，但还需要测验、练习或后续学习记录，才能判断它是否真正帮助了学习。"
    if evidence_status == "process_only":
        return "本次 5E 引导目前只是过程记录。建议继续完成推荐资源、测验或路径节点，让系统获得更完整的学习效果证据。"
    if level in {"引导有效", "基本有效"}:
        return "本次 5E 引导已关联到后续学习结果，可作为学习诊断和路径推荐的辅助证据。"
    return "本次 5E 引导已记录，但后续学习衔接还可以加强，建议继续完成推荐资源或小测。"


def infer_stage_from_response(response: Any) -> str:
    content = str(getattr(response, "content", "") or "").lower()
    buttons = getattr(response, "buttons", []) or []
    resources = getattr(response, "resources", []) or []
    tests = getattr(response, "tests", []) or []
    if tests:
        return "evaluation"
    if resources:
        return "exploration"
    action_text = " ".join(
        str(getattr(item, "show_text", "") or getattr(item, "send_text", "") or "")
        for item in buttons
    ).lower()
    combined = f"{content} {action_text}"
    if any(keyword in combined for keyword in ("评价", "测验", "quiz", "test", "evaluation")):
        return "evaluation"
    if any(keyword in combined for keyword in ("迁移", "应用", "elaboration")):
        return "elaboration"
    if any(keyword in combined for keyword in ("解释", "理解", "explanation")):
        return "explanation"
    if any(keyword in combined for keyword in ("探究", "探索", "resource", "exploration")):
        return "exploration"
    return "engagement"


def _stage_completion_score(stage: str, has_action: bool) -> float:
    try:
        stage_index = STAGE_ORDER.index(stage)
    except ValueError:
        stage_index = 0
    base = (stage_index + 1) / len(STAGE_ORDER) * 100
    if has_action and stage != "evaluation":
        base = min(100.0, base + 10.0)
    return round(base, 2)


def _learning_gain_score(before: Any, after: Any) -> float | None:
    if before is None or after is None:
        return None
    before_score = _clamp(before)
    after_score = _clamp(after)
    gain = after_score - before_score
    if gain <= 0:
        return 40.0 if after_score >= 60 else 20.0
    return round(min(100.0, 50.0 + gain), 2)


def score_interaction_effectiveness(
    response: Any,
    *,
    stage: str | None = None,
    quiz_score_before: float | None = None,
    quiz_score_after: float | None = None,
    path_continue_rate: float | None = None,
) -> dict:
    content = str(getattr(response, "content", "") or "").strip()
    buttons = getattr(response, "buttons", []) or []
    resources = getattr(response, "resources", []) or []
    tests = getattr(response, "tests", []) or []
    has_response = bool(content)
    has_action = bool(buttons or resources or tests)
    inferred_stage = stage or infer_stage_from_response(response)
    interaction_count = 1
    valid_interaction_count = 1 if has_response else 0
    interaction_rate = valid_interaction_count / max(interaction_count, 1) * 100
    if has_response and len(content) >= 20:
        interaction_rate = min(100.0, interaction_rate + 15.0)

    learning_gain = _learning_gain_score(quiz_score_before, quiz_score_after)
    transfer_score = _clamp(path_continue_rate, default=None) if path_continue_rate is not None else None
    if transfer_score is None and has_action:
        transfer_score = 50.0

    evidence_status = "process_only"
    if not has_response:
        evidence_status = "insufficient_evidence"
    elif learning_gain is not None or path_continue_rate is not None:
        evidence_status = "outcome_supported"

    dimension_scores = {
        "stage_completion": _stage_completion_score(inferred_stage, has_action) if has_response else 0.0,
        "valid_interaction": round(_clamp(interaction_rate), 2),
        "learning_gain": learning_gain,
        "learning_transfer": transfer_score,
    }
    weighted_parts = [
        (dimension_scores["stage_completion"], 0.30),
        (dimension_scores["valid_interaction"], 0.30),
    ]
    if learning_gain is not None:
        weighted_parts.append((learning_gain, 0.25))
    if transfer_score is not None:
        weighted_parts.append((transfer_score, 0.15))
    total_weight = sum(weight for _, weight in weighted_parts)
    score = None
    if total_weight > 0 and has_response:
        score = round(sum(score * weight for score, weight in weighted_parts) / total_weight, 2)

    return {
        "interaction_count": interaction_count,
        "valid_interaction_count": valid_interaction_count,
        "completion_rate": 100.0 if has_response else 0.0,
        "effectiveness_score": score,
        "effectiveness_level": _effectiveness_level(score, evidence_status),
        "evidence_status": evidence_status,
        "dimension_scores": dimension_scores,
        "has_action": has_action,
        "stage": inferred_stage,
    }


def record_chat_effectiveness(
    *,
    user_identifier: str,
    course_id: str,
    node_id: str | None,
    session_id: str | None,
    response: Any,
    prompt: str,
) -> dict:
    metrics = score_interaction_effectiveness(response)
    stage = metrics["stage"]
    payload = {
        "summary": "5E 单轮互动有效度记录，仅反映本轮互动质量，不直接改写学生掌握度。",
        "prompt_length": len(str(prompt or "")),
        "response_length": len(str(getattr(response, "content", "") or "")),
        "has_buttons": bool(getattr(response, "buttons", []) or []),
        "has_resources": bool(getattr(response, "resources", []) or []),
        "has_tests": bool(getattr(response, "tests", []) or []),
        "dimension_scores": metrics["dimension_scores"],
        "evidence_status": metrics["evidence_status"],
        "effectiveness_level": metrics["effectiveness_level"],
        "student_feedback": _student_feedback(metrics["effectiveness_level"], metrics["evidence_status"]),
        "mastery_update_policy": "not_updated_by_5e_effectiveness",
    }
    record = {
        "user_identifier": user_identifier,
        "student_username": user_identifier,
        "course_id": course_id,
        "node_id": node_id,
        "session_id": session_id or course_id,
        "stage": stage,
        "interaction_count": metrics["interaction_count"],
        "valid_interaction_count": metrics["valid_interaction_count"],
        "completion_rate": metrics["completion_rate"],
        "effectiveness_score": metrics["effectiveness_score"],
        "payload": payload,
    }
    store = get_database_store()
    if hasattr(store, "record_fivee_effectiveness"):
        record_id = store.record_fivee_effectiveness(**record)
        record["record_id"] = record_id
    return record


def _row_dimension_scores(row: dict, payload: dict) -> dict:
    saved = payload.get("dimension_scores")
    if isinstance(saved, dict):
        return {
            "stage_completion": saved.get("stage_completion"),
            "valid_interaction": saved.get("valid_interaction"),
            "learning_gain": saved.get("learning_gain"),
            "learning_transfer": saved.get("learning_transfer"),
        }
    gain = _learning_gain_score(row.get("quiz_score_before"), row.get("quiz_score_after"))
    transfer = row.get("path_continue_rate")
    return {
        "stage_completion": _stage_completion_score(str(row.get("stage") or "engagement"), bool(payload.get("has_resources") or payload.get("has_tests"))),
        "valid_interaction": round(
            _number(row.get("valid_interaction_count")) / max(_number(row.get("interaction_count")), 1.0) * 100,
            2,
        ),
        "learning_gain": gain,
        "learning_transfer": _clamp(transfer) if transfer is not None else None,
    }


def _row_evidence_status(row: dict, payload: dict) -> str:
    status = str(payload.get("evidence_status") or "").strip()
    if status:
        return status
    if row.get("quiz_score_before") is not None and row.get("quiz_score_after") is not None:
        return "outcome_supported"
    if row.get("path_continue_rate") is not None:
        return "outcome_supported"
    if _number(row.get("valid_interaction_count")) <= 0:
        return "insufficient_evidence"
    return "process_only"


def _average_dimension_scores(rows: list[dict]) -> dict:
    totals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        payload = _parse_payload(row.get("payload") or row.get("payload_json"))
        dimensions = _row_dimension_scores(row, payload)
        for key, value in dimensions.items():
            if value is not None:
                totals[key].append(_clamp(value))
    return {
        key: round(sum(values) / len(values), 2) if values else None
        for key, values in {
            "stage_completion": totals.get("stage_completion", []),
            "valid_interaction": totals.get("valid_interaction", []),
            "learning_gain": totals.get("learning_gain", []),
            "learning_transfer": totals.get("learning_transfer", []),
        }.items()
    }


def build_effectiveness_summary(
    records: Iterable[dict],
    *,
    course_id: str | None = None,
    student_username: str | None = None,
    low_score_threshold: float = 60.0,
) -> dict:
    rows = [dict(item) for item in records if isinstance(item, dict)]
    if not rows:
        return {
            "status": "empty",
            "course_id": course_id,
            "student_username": student_username,
            "record_count": 0,
            "scored_record_count": 0,
            "outcome_supported_count": 0,
            "process_only_count": 0,
            "insufficient_evidence_count": 0,
            "overall_effectiveness_score": None,
            "effectiveness_level": "待计算",
            "evidence_status": "empty",
            "dimension_scores": {
                "stage_completion": None,
                "valid_interaction": None,
                "learning_gain": None,
                "learning_transfer": None,
            },
            "low_score_threshold": low_score_threshold,
            "low_effectiveness_nodes": [],
            "stage_distribution": [],
            "recent_evidence": [],
            "student_view": {
                "show_numeric_score": False,
                "summary": "暂无 5E 引导记录。",
                "next_steps": ["完成一次 5E 提问或继续学习当前课程资源"],
            },
            "teacher_view": {
                "summary": "暂无 5E 有效度记录，不能生成有效度判断。",
                "dimension_scores": {},
                "evidence_policy": "5E 记录只作为学习过程辅助证据，不直接改写学生掌握度。",
            },
            "message": "暂无 5E 有效度记录，不能生成有效度判断。",
        }

    payload_by_index = [_parse_payload(row.get("payload") or row.get("payload_json")) for row in rows]
    evidence_statuses = [_row_evidence_status(row, payload) for row, payload in zip(rows, payload_by_index)]
    scored = [row for row in rows if row.get("effectiveness_score") is not None]
    overall = None
    if scored:
        overall = round(sum(_number(row.get("effectiveness_score")) for row in scored) / len(scored), 2)

    outcome_supported_count = evidence_statuses.count("outcome_supported")
    process_only_count = evidence_statuses.count("process_only")
    insufficient_count = evidence_statuses.count("insufficient_evidence")
    if insufficient_count == len(rows):
        summary_status = "insufficient_evidence"
    elif outcome_supported_count == 0:
        summary_status = "process_only"
    else:
        summary_status = "outcome_supported"
    level = _effectiveness_level(overall, "insufficient_evidence" if summary_status == "insufficient_evidence" else summary_status)
    dimension_scores = _average_dimension_scores(rows)

    stage_counts = Counter(str(row.get("stage") or "unknown") for row in rows)
    node_groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        node_id = str(row.get("node_id") or "").strip()
        if node_id:
            node_groups[node_id].append(row)

    low_nodes = []
    for node_id, node_rows in node_groups.items():
        node_scored = [row for row in node_rows if row.get("effectiveness_score") is not None]
        if not node_scored:
            continue
        avg_score = round(sum(_number(row.get("effectiveness_score")) for row in node_scored) / len(node_scored), 2)
        if avg_score >= low_score_threshold:
            continue
        latest = max(
            node_rows,
            key=lambda row: str(row.get("calculated_at") or row.get("created_at") or ""),
        )
        node_payloads = [_parse_payload(row.get("payload") or row.get("payload_json")) for row in node_rows]
        node_statuses = [_row_evidence_status(row, payload) for row, payload in zip(node_rows, node_payloads)]
        low_nodes.append(
            {
                "node_id": node_id,
                "course_id": latest.get("course_id"),
                "student_count": len({str(row.get("student_username") or row.get("user_identifier") or "") for row in node_rows}),
                "record_count": len(node_rows),
                "avg_effectiveness_score": avg_score,
                "avg_completion_rate": round(
                    sum(_number(row.get("completion_rate")) for row in node_rows) / len(node_rows),
                    2,
                ),
                "avg_valid_interaction_rate": round(
                    sum(
                        _number(row.get("valid_interaction_count")) / max(_number(row.get("interaction_count")), 1.0)
                        for row in node_rows
                    )
                    / len(node_rows)
                    * 100,
                    2,
                ),
                "evidence_status": "outcome_supported" if "outcome_supported" in node_statuses else node_statuses[0],
                "latest_stage": latest.get("stage"),
                "latest_calculated_at": latest.get("calculated_at") or latest.get("created_at"),
            }
        )
    low_nodes.sort(key=lambda item: (item["avg_effectiveness_score"], -item["record_count"]))

    recent_rows = sorted(
        rows,
        key=lambda row: str(row.get("calculated_at") or row.get("created_at") or ""),
        reverse=True,
    )[:10]
    recent_evidence = []
    for row in recent_rows:
        payload = _parse_payload(row.get("payload") or row.get("payload_json"))
        evidence_status = _row_evidence_status(row, payload)
        row_level = str(payload.get("effectiveness_level") or _effectiveness_level(row.get("effectiveness_score"), evidence_status))
        recent_evidence.append(
            {
                "record_id": row.get("record_id"),
                "student_username": row.get("student_username") or row.get("user_identifier"),
                "course_id": row.get("course_id"),
                "node_id": row.get("node_id"),
                "stage": row.get("stage"),
                "effectiveness_score": row.get("effectiveness_score"),
                "effectiveness_level": row_level,
                "evidence_status": evidence_status,
                "dimension_scores": _row_dimension_scores(row, payload),
                "completion_rate": row.get("completion_rate"),
                "interaction_count": row.get("interaction_count"),
                "valid_interaction_count": row.get("valid_interaction_count"),
                "calculated_at": row.get("calculated_at") or row.get("created_at"),
                "summary": payload.get("summary") or payload.get("note") or "",
                "student_feedback": payload.get("student_feedback") or _student_feedback(row_level, evidence_status),
                "mastery_update_policy": payload.get("mastery_update_policy"),
            }
        )

    teacher_summary = (
        "当前 5E 记录只有过程证据，教师可据此优化提示语、资源或测评入口，但不能据此认定学习提升。"
        if summary_status == "process_only"
        else "当前 5E 记录包含后续学习结果证据，可结合低效知识点和证据时间线调整教学支持。"
    )
    if summary_status == "insufficient_evidence":
        teacher_summary = "当前 5E 记录依据不足，建议先补充互动轮次、阶段完成记录、测验或路径完成证据。"

    return {
        "status": "ok",
        "course_id": course_id,
        "student_username": student_username,
        "record_count": len(rows),
        "scored_record_count": len(scored),
        "outcome_supported_count": outcome_supported_count,
        "process_only_count": process_only_count,
        "insufficient_evidence_count": insufficient_count,
        "overall_effectiveness_score": overall,
        "effectiveness_level": level,
        "evidence_status": summary_status,
        "dimension_scores": dimension_scores,
        "low_score_threshold": low_score_threshold,
        "low_effectiveness_nodes": low_nodes,
        "stage_distribution": [
            {"stage": stage, "count": count}
            for stage, count in sorted(stage_counts.items())
        ],
        "recent_evidence": recent_evidence,
        "student_view": {
            "show_numeric_score": False,
            "summary": _student_feedback(level, summary_status),
            "effectiveness_level": level,
            "evidence_status": summary_status,
            "next_steps": ["继续完成推荐资源", "完成一次小测或路径节点", "保留后续学习记录供系统判断"],
        },
        "teacher_view": {
            "summary": teacher_summary,
            "dimension_scores": dimension_scores,
            "evidence_policy": "5E 记录只作为学习过程辅助证据，不直接改写学生掌握度；精确 EES 仅供教师分析。",
        },
        "message": "",
    }


def get_effectiveness_summary(
    *,
    course_id: str | None = None,
    student_username: str | None = None,
    limit: int = 500,
    low_score_threshold: float = 60.0,
) -> dict:
    store = get_database_store()
    if not hasattr(store, "list_fivee_effectiveness_records"):
        return build_effectiveness_summary(
            [],
            course_id=course_id,
            student_username=student_username,
            low_score_threshold=low_score_threshold,
        )
    records = store.list_fivee_effectiveness_records(
        course_id=course_id,
        student_username=student_username,
        limit=limit,
    )
    return build_effectiveness_summary(
        records,
        course_id=course_id,
        student_username=student_username,
        low_score_threshold=low_score_threshold,
    )


def _merge_outcome_payload(existing_payload: Any, metrics: dict, outcome_type: str, extra: dict | None = None) -> dict:
    payload = _parse_payload(existing_payload)
    outcome = dict(extra or {})
    outcome["type"] = outcome_type
    outcome["evidence_status"] = metrics["evidence_status"]
    payload.update(
        {
            "summary": "5E 引导已关联到后续学习结果，仍仅作为诊断和路径推荐的辅助证据。",
            "dimension_scores": metrics["dimension_scores"],
            "evidence_status": metrics["evidence_status"],
            "effectiveness_level": metrics["effectiveness_level"],
            "student_feedback": _student_feedback(metrics["effectiveness_level"], metrics["evidence_status"]),
            "mastery_update_policy": "not_updated_by_5e_effectiveness",
            "outcome_link": outcome,
        }
    )
    return payload


def link_quiz_outcome(
    *,
    student_username: str,
    course_id: str | None,
    node_id: str | None,
    quiz_score_after: float,
    quiz_score_before: float | None = None,
) -> dict:
    """Attach a later quiz result to the latest matching 5E record as outcome evidence."""
    store = get_database_store()
    records = []
    if hasattr(store, "list_fivee_effectiveness_records"):
        records = store.list_fivee_effectiveness_records(
            course_id=course_id,
            student_username=student_username,
            limit=20,
        )
    target = next(
        (
            record for record in records
            if str(record.get("node_id") or "").strip() == str(node_id or "").strip()
        ),
        records[0] if records else None,
    )
    if not target:
        return {"updated": False, "reason": "no_recent_fivee_record"}

    response_stub = type("FiveEOutcomeStub", (), {"content": "linked quiz outcome", "buttons": [], "resources": [], "tests": []})()
    before = quiz_score_before
    if before is None and target.get("quiz_score_before") is not None:
        before = target.get("quiz_score_before")
    metrics = score_interaction_effectiveness(
        response_stub,
        stage=str(target.get("stage") or "evaluation"),
        quiz_score_before=before,
        quiz_score_after=quiz_score_after,
        path_continue_rate=target.get("path_continue_rate"),
    )
    payload = _merge_outcome_payload(
        target.get("payload") or target.get("payload_json"),
        metrics,
        "quiz_outcome",
        {
            "quiz_score_before": before,
            "quiz_score_after": quiz_score_after,
            "node_id": node_id,
        },
    )
    updater = getattr(store, "update_fivee_effectiveness_outcome", None)
    if not callable(updater):
        return {"updated": False, "reason": "store_update_not_supported"}
    updated = updater(
        record_id=target.get("record_id"),
        quiz_score_before=before,
        quiz_score_after=quiz_score_after,
        path_continue_rate=target.get("path_continue_rate"),
        effectiveness_score=metrics["effectiveness_score"],
        payload=payload,
    )
    return {
        "updated": bool(updated),
        "record_id": target.get("record_id"),
        "effectiveness_score": metrics["effectiveness_score"],
        "evidence_status": metrics["evidence_status"],
        "mastery_update_policy": payload["mastery_update_policy"],
    }


def link_path_continuation(
    *,
    student_username: str,
    course_id: str | None,
    node_id: str | None,
    path_continue_rate: float = 100.0,
) -> dict:
    """Attach path-node continuation/completion to the latest matching 5E record."""
    store = get_database_store()
    records = []
    if hasattr(store, "list_fivee_effectiveness_records"):
        records = store.list_fivee_effectiveness_records(
            course_id=course_id,
            student_username=student_username,
            limit=20,
        )
    target = next(
        (
            record for record in records
            if str(record.get("node_id") or "").strip() == str(node_id or "").strip()
        ),
        records[0] if records else None,
    )
    if not target:
        return {"updated": False, "reason": "no_recent_fivee_record"}

    response_stub = type("FiveEOutcomeStub", (), {"content": "linked path continuation", "buttons": [], "resources": [], "tests": []})()
    metrics = score_interaction_effectiveness(
        response_stub,
        stage=str(target.get("stage") or "elaboration"),
        quiz_score_before=target.get("quiz_score_before"),
        quiz_score_after=target.get("quiz_score_after"),
        path_continue_rate=path_continue_rate,
    )
    payload = _merge_outcome_payload(
        target.get("payload") or target.get("payload_json"),
        metrics,
        "path_continuation",
        {
            "path_continue_rate": path_continue_rate,
            "node_id": node_id,
        },
    )
    updater = getattr(store, "update_fivee_effectiveness_outcome", None)
    if not callable(updater):
        return {"updated": False, "reason": "store_update_not_supported"}
    updated = updater(
        record_id=target.get("record_id"),
        quiz_score_before=target.get("quiz_score_before"),
        quiz_score_after=target.get("quiz_score_after"),
        path_continue_rate=path_continue_rate,
        effectiveness_score=metrics["effectiveness_score"],
        payload=payload,
    )
    return {
        "updated": bool(updated),
        "record_id": target.get("record_id"),
        "effectiveness_score": metrics["effectiveness_score"],
        "evidence_status": metrics["evidence_status"],
        "mastery_update_policy": payload["mastery_update_policy"],
    }
