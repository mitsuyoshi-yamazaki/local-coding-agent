"""道具の入力を、定義の入力の形（JSON Schema）と照らす。

モデルは、定義に合わない入力（必須の欄が無い・型が違う）で道具を呼ぶことがある。実行の前に
ハーネスが照らし、合わなければ、どこが合わないかを誤りの結果としてモデルに返す。

照らすのは、このリポジトリの道具が使う範囲だけである: 必須の欄（required）・欄の型（type）・
数の下限（minimum）。定義に無い欄は見ない。
"""

import json
from collections.abc import Mapping

# JSON Schema の型と、json.loads が返す Python の型
_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "object": (dict,),
    "array": (list,),
    "null": (type(None),),
}


def input_problem(
    schema: Mapping[str, object], value: Mapping[str, object]
) -> str | None:
    """入力が定義に合わなければ、どこが合わないかの文を返す。合えば None。"""
    required = schema.get("required", [])
    names = required if isinstance(required, list) else []
    missing = [str(name) for name in names if name not in value]
    if missing:
        return f"必須の欄が無い: {', '.join(missing)}"
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return None
    for name, item in value.items():
        rule = properties.get(name)
        problem = (
            _property_problem(name, rule, item) if isinstance(rule, dict) else None
        )
        if problem is not None:
            return problem
    return None


def _property_problem(name: str, rule: dict[str, object], item: object) -> str | None:
    expected = rule.get("type")
    if isinstance(expected, str) and not _has_type(item, expected):
        return f"{name} は {expected} でなければならない（受けた値: {_shown(item)}）"
    minimum = rule.get("minimum")
    if _below(item, minimum):
        return f"{name} は {minimum} 以上でなければならない（受けた値: {_shown(item)}）"
    return None


def _has_type(item: object, expected: str) -> bool:
    # bool は int の一種だが、JSON では真偽値と数は別の型である
    if isinstance(item, bool) and expected != "boolean":
        return False
    return isinstance(item, _TYPES.get(expected, (object,)))


def _below(item: object, minimum: object) -> bool:
    """item と minimum がどちらも数で、item が minimum より小さいか。"""
    if isinstance(item, bool) or isinstance(minimum, bool):
        return False
    numbers = (int, float)
    return isinstance(item, numbers) and isinstance(minimum, numbers) and item < minimum


def _shown(item: object) -> str:
    return json.dumps(item, ensure_ascii=False)
