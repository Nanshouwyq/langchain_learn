"""把本地 eval_cases.json 同步到 LangSmith Dataset。

用法（项目根目录）：
  python -m note_assistant.eval.upload_langsmith
  python -m note_assistant.eval.upload_langsmith --name note-assistant-eval
  python -m note_assistant.eval.upload_langsmith --replace
  python -m note_assistant.eval.upload_langsmith --type rag

依赖：.env 中已配置 LANGSMITH_API_KEY（及可选 LANGSMITH_ENDPOINT）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from langsmith import Client


DEFAULT_DATASET = "note-assistant-eval"


def _load_cases(path: Path) -> tuple[str, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("description") or "", data["cases"]


def _to_example(case: dict) -> dict:
    """本地 case → LangSmith example（inputs / outputs / metadata）。"""
    inputs = {
        "question": case["question"],
        "type": case.get("type", "rag"),
    }
    # 写操作 fixture：评测 target 可按需读取
    for key in ("setup_title", "setup_content", "setup_tags", "cleanup_title"):
        if case.get(key):
            inputs[key] = case[key]

    outputs = {
        "must_include": case.get("must_include") or [],
        "must_include_any": case.get("must_include_any") or [],
        "must_not_include": case.get("must_not_include") or [],
    }
    metadata = {
        "case_id": case.get("id", ""),
        "note": case.get("note", ""),
        "type": case.get("type", "rag"),
    }
    return {"inputs": inputs, "outputs": outputs, "metadata": metadata}


def sync_dataset(
    cases_path: Path,
    dataset_name: str,
    *,
    replace: bool = False,
    case_type: str | None = None,
) -> None:
    description, cases = _load_cases(cases_path)
    if case_type:
        cases = [c for c in cases if c.get("type", "rag") == case_type]
    if not cases:
        raise SystemExit("没有可上传的用例")

    examples = [_to_example(c) for c in cases]
    client = Client()

    existing = None
    try:
        existing = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        existing = None

    if existing and replace:
        print(f"删除已有数据集: {dataset_name} ({existing.id})")
        client.delete_dataset(dataset_id=existing.id)
        existing = None

    if existing is None:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=description or "笔记助手评测黄金集",
        )
        print(f"已创建数据集: {dataset.name} ({dataset.id})")
    else:
        dataset = existing
        print(f"使用已有数据集: {dataset.name} ({dataset.id})")
        if not replace:
            print("提示: 将追加 examples；若要覆盖请加 --replace")

    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"已上传 {len(examples)} 条 examples → dataset「{dataset_name}」")
    print("打开 LangSmith → Datasets 查看；可用 evaluate() 对该 dataset 跑评测。")


def main() -> None:
    parser = argparse.ArgumentParser(description="同步 eval_cases 到 LangSmith")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("eval_cases.json"),
    )
    parser.add_argument("--name", default=DEFAULT_DATASET, help="Dataset 名称")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="删除同名 dataset 后重建（覆盖）",
    )
    parser.add_argument(
        "--type",
        choices=["rag", "agent"],
        default=None,
        help="只上传指定类型",
    )
    args = parser.parse_args()
    sync_dataset(
        args.cases,
        args.name,
        replace=args.replace,
        case_type=args.type,
    )


if __name__ == "__main__":
    main()
