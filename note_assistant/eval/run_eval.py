"""笔记助手评测迷你版

用法（在项目根目录）：
  python -m note_assistant.eval.run_eval
  python -m note_assistant.eval.run_eval --limit 2
  python -m note_assistant.eval.run_eval --type rag
  python -m note_assistant.eval.run_eval --type agent
  python -m note_assistant.eval.run_eval --cases note_assistant/eval/eval_cases.json

说明：
  - type=rag：走 ask_notes（纯 RAG）
  - type=agent：走 Agent（增删改查工具）
  - 用 must_include / must_not_include 做规则打分（入门够用）
  - setup_title / cleanup_title：评测前后自动准备/清理临时笔记
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

# 允许直接 python note_assistant/eval/run_eval.py
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from note_assistant.chains import ask_notes
from note_assistant.config import NOTES_DIR
from note_assistant.service import agent_chat


def _load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cases"]


def _note_path(title: str) -> Path:
    return NOTES_DIR / f"{title.replace(' ', '_')}.md"


def _setup_case(case: dict) -> None:
    title = case.get("setup_title")
    if not title:
        return
    content = case.get("setup_content") or "评测占位内容"
    tags = case.get("setup_tags") or "评测"
    path = _note_path(title)
    path.write_text(
        f"# {title}\n\n**标签**: {tags}\n\n{content}\n",
        encoding="utf-8",
    )


def _cleanup_case(case: dict) -> None:
    title = case.get("cleanup_title") or case.get("setup_title")
    if not title:
        return
    path = _note_path(title)
    if path.exists():
        path.unlink()


def _score(answer: str, case: dict) -> tuple[bool, list[str]]:
    text = (answer or "").lower()
    problems: list[str] = []
    for kw in case.get("must_include") or []:
        if kw.lower() not in text:
            problems.append(f"缺少关键词: {kw}")
    any_list = case.get("must_include_any") or []
    if any_list and not any(kw.lower() in text for kw in any_list):
        problems.append(f"至少应包含其一: {any_list}")
    for kw in case.get("must_not_include") or []:
        if kw.lower() in text:
            problems.append(f"不应出现: {kw}")
    return (len(problems) == 0, problems)


def _run_case(case: dict) -> str:
    q = case["question"]
    case_type = case.get("type", "rag")
    if case_type == "rag":
        return ask_notes(q)
    if case_type == "agent":
        # 每条用例独立会话，避免工具历史互相污染
        result = agent_chat(q, session_id=f"eval-{case['id']}-{uuid4().hex[:8]}")
        return result.get("reply") or ""
    raise ValueError(f"暂不支持 type={case_type}")


def run_eval(
    cases_path: Path,
    limit: int | None = None,
    case_type: str | None = None,
) -> dict:
    cases = _load_cases(cases_path)
    if case_type:
        cases = [c for c in cases if c.get("type", "rag") == case_type]
    if limit is not None:
        cases = cases[:limit]

    results = []
    passed = 0
    for case in cases:
        q = case["question"]
        _setup_case(case)
        t0 = time.time()
        try:
            answer = _run_case(case)
            err = None
        except Exception as e:
            answer = ""
            err = str(e)
        finally:
            _cleanup_case(case)
        latency = round(time.time() - t0, 2)

        ok, problems = (False, [err]) if err else _score(answer, case)
        if ok:
            passed += 1

        row = {
            "id": case["id"],
            "pass": ok,
            "latency_sec": latency,
            "question": q,
            "answer": answer[:500],
            "problems": problems,
            "note": case.get("note", ""),
        }
        results.append(row)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['id']} ({latency}s) {q}")
        if problems:
            print(f"       -> {'; '.join(problems)}")

    summary = {
        "total": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 3) if results else 0.0,
        "results": results,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="笔记助手迷你评测（RAG + 增删改查）")
    default_cases = Path(__file__).with_name("eval_cases.json")
    parser.add_argument("--cases", type=Path, default=default_cases)
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条")
    parser.add_argument(
        "--type",
        choices=["rag", "agent"],
        default=None,
        help="只跑指定类型（rag / agent）",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("note_assistant/eval/last_report.json"),
        help="结果 JSON 输出路径",
    )
    args = parser.parse_args()

    print(f"加载用例: {args.cases}")
    summary = run_eval(args.cases, limit=args.limit, case_type=args.type)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"\n汇总: {summary['passed']}/{summary['total']} "
        f"pass_rate={summary['pass_rate']}"
    )
    print(f"报告已写入: {args.out}")


if __name__ == "__main__":
    main()

