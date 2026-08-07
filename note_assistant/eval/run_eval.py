"""笔记助手评测迷你版

用法（在项目根目录）：
  python -m note_assistant.eval.run_eval
  python -m note_assistant.eval.run_eval --limit 2
  python -m note_assistant.eval.run_eval --cases note_assistant/eval/eval_cases.json

说明：
  - 默认走 ask_notes（纯 RAG），快、好定位「检索/生成」问题
  - 用 must_include / must_not_include 做规则打分（入门够用）
  - 改 Prompt / 切分 / TopK 后重跑，对比 pass_rate
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 允许直接 python note_assistant/eval/run_eval.py
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from note_assistant.chains import ask_notes


def _load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cases"]


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


def run_eval(cases_path: Path, limit: int | None = None) -> dict:
    cases = _load_cases(cases_path)
    if limit is not None:
        cases = cases[:limit]

    results = []
    passed = 0
    for case in cases:
        q = case["question"]
        t0 = time.time()
        try:
            if case.get("type", "rag") == "rag":
                answer = ask_notes(q)
            else:
                answer = f"[跳过] 暂不支持 type={case.get('type')}"
            err = None
        except Exception as e:
            answer = ""
            err = str(e)
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
    parser = argparse.ArgumentParser(description="笔记助手 RAG 迷你评测")
    default_cases = Path(__file__).with_name("eval_cases.json")
    parser.add_argument("--cases", type=Path, default=default_cases)
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("note_assistant/eval/last_report.json"),
        help="结果 JSON 输出路径",
    )
    args = parser.parse_args()

    print(f"加载用例: {args.cases}")
    summary = run_eval(args.cases, limit=args.limit)
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
