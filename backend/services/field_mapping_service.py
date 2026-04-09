from __future__ import annotations

import io
import json
import logging
import re
from typing import Dict, List

import pandas as pd

from config.settings import LLMSettings
from services.llm_client import LLMClient
from services.schema_models import ExtractionField, ExtractionPlan


LOGGER = logging.getLogger("compare_tasks")

FIELD_DEFAULT_TYPES = {
    "date": "date",
    "order_no": "string",
    "factory": "string",
    "model": "string",
    "company": "string",
    "quantity": "integer",
}

REQUIRED_FIELDS_BY_ROLE = {
    "factory": ("order_no", "quantity"),
    "jiuding": ("order_no", "quantity", "company"),
}

FACTORY_COMPANY_KEYWORDS = {
    "hengyi": ["送达方", "售达方", "客户名称", "客户", "会员名称", "会员"],
    "xinfengming": ["客户名称", "送达方", "售达方", "公司", "会员名称", "会员", "客户"],
}

FALLBACK_KEYWORDS = {
    "factory": {
        "date": ["交货日期", "日期", "创建日期", "时间"],
        "order_no": ["交货单号", "交货单", "订单号", "订单", "单号"],
        "factory": ["工厂", "工厂名称", "生产工厂", "销售组织描述"],
        "company": ["送达方", "售达方", "客户名称", "客户", "会员名称", "会员"],
        "quantity": ["交货数量", "实际数量", "数量", "件数", "出库数量"],
    },
    "jiuding": {
        "date": ["订单日期", "日期", "创建日期", "时间"],
        "order_no": ["出库单号", "订单号", "订单", "单号"],
        "factory": ["工厂", "工厂名称"],
        "model": ["产品类型", "产品", "物料", "品种"],
        "company": ["会员名称", "会员", "公司", "客户名称", "客户"],
        "quantity": ["实际出库数量", "出库数量", "数量", "件数"],
    },
}

MODEL_SIGNAL_TOKENS = ("POY", "FDY", "DTY", "HOY", "ITY")


def _normalize_column_name(value: str) -> str:
    return str(value).strip()


def _json_dumps(data: Dict) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _find_column(columns: List[str], keywords: List[str]) -> str:
    for keyword in keywords:
        for column in columns:
            normalized = _normalize_column_name(column)
            if keyword in normalized:
                return normalized
    raise ValueError(f"Could not identify column for keywords: {keywords}")


def _find_column_optional(columns: List[str], keywords: List[str]) -> str | None:
    try:
        return _find_column(columns, keywords)
    except ValueError:
        return None


def _sample_non_empty_rows(df: pd.DataFrame, limit: int) -> List[Dict[str, str]]:
    sampled_rows: List[Dict[str, str]] = []
    first_column = df.columns[0] if len(df.columns) > 0 else None
    if first_column is None:
        return sampled_rows

    for _, row in df.iterrows():
        first_value = row.get(first_column)
        if first_value is None or pd.isna(first_value) or str(first_value).strip() == "":
            continue

        sampled_rows.append(
            {
                _normalize_column_name(column): (
                    "" if row.get(column) is None or pd.isna(row.get(column)) else str(row.get(column)).strip()
                )
                for column in df.columns
            }
        )
        if len(sampled_rows) >= limit:
            break

    return sampled_rows


def build_jiuding_reference_samples(file_contents: List[bytes]) -> List[Dict[str, str]]:
    collected_rows: List[Dict[str, str]] = []
    for file_content in file_contents:
        df = pd.read_excel(io.BytesIO(file_content), dtype=str)
        df.columns = [_normalize_column_name(column) for column in df.columns]
        collected_rows.extend(_sample_non_empty_rows(df, 5))
        if len(collected_rows) >= 5:
            break
    return collected_rows[:5]


def _build_prompt(
    *,
    role: str,
    factory_type: str,
    filename: str,
    columns: List[str],
    markdown: str,
    preview: str,
    sampled_rows: List[Dict[str, str]],
    jiuding_reference_rows: List[Dict[str, str]],
) -> str:
    return (
        f"任务角色: {role}\n"
        f"工厂角色: {factory_type}\n"
        f"文件名: {filename}\n"
        "你是 Excel 对账字段识别助手，只能返回 JSON，不能输出解释性文字。\n"
        "你的目标不是看表头猜字段，而是要结合两端样本值，识别真实业务语义。\n"
        "必须识别的字段键为: date, order_no, factory, model, company, quantity。\n\n"
        "核心规则:\n"
        "1. order_no 表示订单号/交货单号/出库单号，必须按字符串精确匹配，绝不能当数字处理，绝不能丢失前导零。\n"
        "2. quantity 表示数量/出库数量，必须是数值字段。\n"
        "3. company 的业务语义必须与久鼎侧“会员名称”一致。工厂侧的送达方、售达方、客户名称等通常属于 company，不是 factory。\n"
        "4. factory 只表示真正的工厂、工厂简称或销售组织对应的工厂信息，不能把普通客户名称、会员名称误判成 factory。\n"
        "5. model 表示产品类型语义字段。你必须拿久鼎参考样本中的“产品类型”值，去比较工厂侧每一列的样本值，找出语义最接近的那一列。\n"
        "6. 对于 model，不能依赖固定列名，不能假设工厂侧一定叫某个表头。即使列名完全陌生，只要样本值与久鼎侧产品类型值最接近，也应映射为 model。\n"
        "7. 如果字段不确定，不要乱选；但对 model 必须先完成逐列样本值比对后再决定。\n"
        "8. 对久鼎侧数据，如果存在“会员名称”列，company 必须优先映射到“会员名称”，不能误选“客户名称”或“公司”。\n"
        "9. 只有在完全找不到高相似字段时，才允许省略 date、factory、model；但 order_no 和 quantity 不能省略。\n\n"
        "输出要求:\n"
        "- 一列只能映射到一个字段。\n"
        "- notes 中简要写出你的判断依据，尤其说明 model 是如何基于样本值比较得出的。\n"
        "- 返回严格 JSON，包含 source_sheet, header_row_index, data_start_row_index, skip_keywords, fields, confidence, notes。\n\n"
        f"当前文件全部列名: {columns}\n"
        f"当前文件抽样行（3行，保留全部列）: {sampled_rows}\n"
        f"久鼎参考样本（5行，保留全部列）: {jiuding_reference_rows}\n\n"
        f"Markdown 预览:\n{markdown[:8000]}\n\n"
        f"表格预览:\n{preview[:4000]}"
    )


def _normalize_plan_payload(payload: Dict) -> Dict:
    normalized = dict(payload)

    notes = normalized.get("notes")
    if isinstance(notes, str):
        normalized["notes"] = [notes]
    elif notes is None:
        normalized["notes"] = []

    fields = normalized.get("fields", {})
    normalized_fields = {}
    for field_name, field_payload in fields.items():
        if isinstance(field_payload, str):
            normalized_field = {"column": field_payload}
        elif isinstance(field_payload, dict):
            normalized_field = dict(field_payload)
        else:
            continue

        if "column" not in normalized_field and "source_column" in normalized_field:
            normalized_field["column"] = normalized_field["source_column"]

        column_value = normalized_field.get("column")
        if column_value is None or not str(column_value).strip():
            continue

        normalized_field["column"] = str(column_value).strip()

        if "type" not in normalized_field and "data_type" in normalized_field:
            normalized_field["type"] = normalized_field["data_type"]
        if "type" not in normalized_field:
            normalized_field["type"] = FIELD_DEFAULT_TYPES.get(field_name, "string")

        if field_name == "date" and "output_format" not in normalized_field:
            normalized_field["output_format"] = "yyyy/m/d"

        normalized_fields[field_name] = normalized_field

    normalized["fields"] = normalized_fields
    return normalized


def _prefer_company_column(columns: List[str], factory_type: str) -> str | None:
    return _find_column_optional(columns, FACTORY_COMPANY_KEYWORDS.get(factory_type, []))


def _looks_like_model_key(column_name: str) -> bool:
    normalized = _normalize_column_name(column_name)
    return "产品类型" in normalized or "型号" in normalized


def _collect_reference_model_values(jiuding_reference_rows: List[Dict[str, str]] | None) -> List[str]:
    if not jiuding_reference_rows:
        return []

    values: List[str] = []
    seen: set[str] = set()
    for row in jiuding_reference_rows:
        for key, value in row.items():
            if not _looks_like_model_key(key):
                continue

            text = str(value).strip().upper()
            if not text or text in seen:
                continue

            seen.add(text)
            values.append(text)
    return values


def _extract_model_tokens(text: str) -> List[str]:
    upper_text = text.upper()
    tokens: List[str] = []
    seen: set[str] = set()

    for candidate in re.findall(r"[A-Z]{2,}(?:[/-][A-Z0-9]+)?", upper_text):
        if candidate not in seen:
            seen.add(candidate)
            tokens.append(candidate)

    for candidate in re.findall(r"\d+(?:\.\d+)?DTEX|\d+F|\d+D/\d+F", upper_text):
        if candidate not in seen:
            seen.add(candidate)
            tokens.append(candidate)

    return tokens


def _collect_reference_model_tokens(reference_values: List[str]) -> List[str]:
    tokens: List[str] = []
    seen: set[str] = set()

    for value in reference_values:
        for token in _extract_model_tokens(value):
            if token not in seen:
                seen.add(token)
                tokens.append(token)

    return tokens


def _score_model_value(text: str, *, reference_values: List[str], reference_tokens: List[str]) -> int:
    upper_text = str(text).strip().upper()
    if not upper_text:
        return 0

    score = 0
    if any(reference_value in upper_text or upper_text in reference_value for reference_value in reference_values):
        score += 6

    matched_tokens = [token for token in reference_tokens if token in upper_text]
    score += len(matched_tokens) * 4

    if matched_tokens and any(signal in upper_text for signal in MODEL_SIGNAL_TOKENS):
        score += 2

    if re.search(r"\d+(?:\.\d+)?DTEX|\d+F|\d+D/\d+F", upper_text):
        score += 1

    return score


def _infer_model_column_from_samples(
    df: pd.DataFrame,
    *,
    excluded_columns: set[str],
    jiuding_reference_rows: List[Dict[str, str]] | None,
) -> str | None:
    reference_values = _collect_reference_model_values(jiuding_reference_rows)
    if not reference_values:
        return None

    reference_tokens = _collect_reference_model_tokens(reference_values)
    best_column: str | None = None
    best_score = 0
    columns = [str(column).strip() for column in df.columns]

    for column in columns:
        if column in excluded_columns:
            continue

        values = [
            str(value).strip()
            for value in df[column].fillna("").tolist()
            if str(value).strip()
        ][:30]
        if not values:
            continue

        column_score = sum(
            _score_model_value(value, reference_values=reference_values, reference_tokens=reference_tokens)
            for value in values
        )
        if column_score > best_score:
            best_score = column_score
            best_column = column

    return best_column if best_score > 0 else None


def _apply_semantic_corrections(
    normalized_payload: Dict,
    *,
    df: pd.DataFrame,
    role: str,
    factory_type: str,
    jiuding_reference_rows: List[Dict[str, str]] | None,
) -> Dict:
    corrected = dict(normalized_payload)
    corrected_fields = dict(corrected.get("fields", {}))
    correction_notes = list(corrected.get("notes", []))
    columns = [str(column).strip() for column in df.columns]

    if role == "jiuding":
        member_name_column = _find_column_optional(columns, ["会员名称", "会员"])
        if member_name_column:
            current_company = corrected_fields.get("company", {}).get("column")
            if current_company != member_name_column:
                corrected_fields["company"] = {
                    "column": member_name_column,
                    "type": "string",
                }
                correction_notes.append("久鼎侧 company 已修正为会员名称列")

    if role == "factory":
        excluded_columns = {
            field_payload.get("column")
            for field_name, field_payload in corrected_fields.items()
            if field_name != "model" and isinstance(field_payload, dict)
        }
        inferred_model_column = _infer_model_column_from_samples(
            df,
            excluded_columns={column for column in excluded_columns if column},
            jiuding_reference_rows=jiuding_reference_rows,
        )
        current_model = corrected_fields.get("model", {}).get("column")
        if inferred_model_column and current_model != inferred_model_column:
            corrected_fields["model"] = {
                "column": inferred_model_column,
                "type": "string",
            }
            correction_notes.append("factory model 已按久鼎产品类型样本值相似度修正")

    corrected["fields"] = corrected_fields
    corrected["notes"] = correction_notes
    return corrected


def _merge_missing_fields_with_fallbacks(
    normalized_payload: Dict,
    *,
    df: pd.DataFrame,
    columns: List[str],
    role: str,
    factory_type: str,
    jiuding_reference_rows: List[Dict[str, str]] | None,
) -> Dict:
    merged = dict(normalized_payload)
    merged_fields = dict(merged.get("fields", {}))
    fallback_keywords = FALLBACK_KEYWORDS[role]
    missing_fields = []

    for field_name, keywords in fallback_keywords.items():
        if field_name in merged_fields:
            continue

        if role == "factory" and field_name == "company":
            inferred_column = _prefer_company_column(columns, factory_type) or _find_column_optional(columns, keywords)
        else:
            inferred_column = _find_column_optional(columns, keywords)

        if inferred_column is None:
            continue

        merged_fields[field_name] = {
            "column": inferred_column,
            "type": FIELD_DEFAULT_TYPES.get(field_name, "string"),
            **({"output_format": "yyyy/m/d"} if field_name == "date" else {}),
        }
        missing_fields.append(field_name)

    if role == "factory" and "model" not in merged_fields:
        excluded_columns = {
            field_payload.get("column")
            for field_payload in merged_fields.values()
            if isinstance(field_payload, dict) and field_payload.get("column")
        }
        inferred_model_column = _infer_model_column_from_samples(
            df,
            excluded_columns={column for column in excluded_columns if column},
            jiuding_reference_rows=jiuding_reference_rows,
        )
        if inferred_model_column:
            merged_fields["model"] = {
                "column": inferred_model_column,
                "type": "string",
            }
            missing_fields.append("model")

    merged["fields"] = merged_fields
    if missing_fields:
        merged["notes"] = [
            *merged.get("notes", []),
            f"补齐字段: {', '.join(missing_fields)}",
        ]

    return _apply_semantic_corrections(
        merged,
        df=df,
        role=role,
        factory_type=factory_type,
        jiuding_reference_rows=jiuding_reference_rows,
    )


def _validate_required_fields(normalized_payload: Dict, *, role: str) -> None:
    fields = normalized_payload.get("fields", {})
    required_fields = REQUIRED_FIELDS_BY_ROLE.get(role, ("order_no", "quantity"))
    missing_required = [field_name for field_name in required_fields if field_name not in fields]
    if missing_required:
        raise ValueError(f"Missing required fields for {role}: {', '.join(missing_required)}")


def _heuristic_plan(df: pd.DataFrame, role: str, factory_type: str) -> ExtractionPlan:
    columns = [_normalize_column_name(column) for column in df.columns]
    fields: Dict[str, ExtractionField] = {}

    for field_name, keywords in FALLBACK_KEYWORDS[role].items():
        if role == "factory" and field_name == "company":
            column = _prefer_company_column(columns, factory_type) or _find_column_optional(columns, keywords)
        else:
            required_fields = set(REQUIRED_FIELDS_BY_ROLE.get(role, ("order_no", "quantity")))
            column = _find_column(columns, keywords) if field_name in required_fields else _find_column_optional(columns, keywords)

        if column is None:
            continue

        fields[field_name] = ExtractionField(
            column=column,
            type=FIELD_DEFAULT_TYPES[field_name],
            output_format="yyyy/m/d" if field_name == "date" else None,
        )

    plan = ExtractionPlan(
        source_sheet=None,
        header_row_index=1,
        data_start_row_index=2,
        skip_keywords=["合计", "汇总", "总计", "备注"],
        fields=fields,
        confidence=0.2,
        notes=["heuristic fallback plan"],
    )
    return plan


def build_extraction_plan(
    *,
    file_content: bytes,
    filename: str,
    role: str,
    factory_type: str,
    markdown: str,
    preview: str,
    llm_settings: LLMSettings,
    jiuding_reference_rows: List[Dict[str, str]] | None = None,
) -> ExtractionPlan:
    df = pd.read_excel(io.BytesIO(file_content), dtype=str)
    df.columns = [_normalize_column_name(column) for column in df.columns]
    columns = [str(column) for column in df.columns]

    if role == "jiuding":
        plan = _heuristic_plan(df, role, factory_type)
        LOGGER.info(
            "filename=%s role=%s mapping_strategy=heuristic plan=%s",
            filename,
            role,
            _json_dumps(plan.model_dump()),
        )
        return plan

    if not llm_settings.is_configured:
        plan = _heuristic_plan(df, role, factory_type)
        LOGGER.info(
            "filename=%s role=%s mapping_strategy=heuristic_no_llm plan=%s",
            filename,
            role,
            _json_dumps(plan.model_dump()),
        )
        return plan

    sampled_rows = _sample_non_empty_rows(df, 3)
    system_prompt = (
        "You are an extraction planner for Excel comparison tasks. "
        "Return strict JSON only. "
        "The JSON must include source_sheet, header_row_index, data_start_row_index, skip_keywords, "
        "fields, confidence, and notes."
    )
    user_prompt = _build_prompt(
        role=role,
        factory_type=factory_type,
        filename=filename,
        columns=columns,
        markdown=markdown,
        preview=preview,
        sampled_rows=sampled_rows,
        jiuding_reference_rows=jiuding_reference_rows or [],
    )
    payload = LLMClient(llm_settings).generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    normalized_payload = _normalize_plan_payload(payload)
    merged_payload = _merge_missing_fields_with_fallbacks(
        normalized_payload,
        df=df,
        columns=columns,
        role=role,
        factory_type=factory_type,
        jiuding_reference_rows=jiuding_reference_rows,
    )

    LOGGER.info(
        "filename=%s role=%s raw_mapping=%s normalized_mapping=%s final_mapping=%s",
        filename,
        role,
        _json_dumps(payload),
        _json_dumps(normalized_payload),
        _json_dumps(merged_payload),
    )

    _validate_required_fields(merged_payload, role=role)
    return ExtractionPlan.model_validate(merged_payload)
