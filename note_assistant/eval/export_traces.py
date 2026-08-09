"""从 LangSmith 导出 tracing，落到本地做延迟 / 错误分析。

用法（项目根目录）：
  python -m note_assistant.eval.export_traces
  python -m note_assistant.eval.export_traces --limit 20 --days 2
  python -m note_assistant.eval.export_traces --run-id <root_run_id>
  python -m note_assistant.eval.export_traces --name ChatOpenAI --limit 50

依赖：.env 中 LANGSMITH_API_KEY、LANGSMITH_PROJECT。
导出目录：note_assistant/eval/traces/<时间戳>/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from langsmith import Client


TRACES_DIR = Path(__file__).resolve().parent / "traces"


def _dt(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _latency_ms(run) -> float | None:
    start = getattr(run, "start_time", None)
    end = getattr(run, "end_time", None)
    if not start or not end:
        return getattr(run, "total_tokens", None) and None
    try:
        return round((end - start).total_seconds() * 1000, 1)
    except Exception:
        return None


def _run_to_dict(run, *, include_io: bool = True) -> dict:
    row = {
        "id": str(run.id),
        "trace_id": str(run.trace_id) if run.trace_id else None,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "name": run.name,
        "run_type": run.run_type,
        "status": getattr(run, "status", None),
        "start_time": _dt(run.start_time),
        "end_time": _dt(run.end_time),
        "latency_ms": _latency_ms(run),
        "error": run.error,
        "tags": list(run.tags or []),
    }
    if include_io:
        # 输入输出可能很大，截断字符串字段
        row["inputs"] = _truncate(run.inputs)
        row["outputs"] = _truncate(run.outputs)
    usage = getattr(run, "total_tokens", None) or getattr(run, "prompt_tokens", None)
    meta = getattr(run, "extra", None) or {}
    if isinstance(meta, dict):
        row["extra_keys"] = sorted(meta.keys())[:20]
    if usage is not None:
        row["total_tokens"] = usage
    # token 用量常见在 extra.metadata 或 usage_metadata
    for attr in ("prompt_tokens", "completion_tokens", "total_cost"):
        val = getattr(run, attr, None)
        if val is not None:
            row[attr] = val
    return row


def _truncate(obj: Any, max_str: int = 2000) -> Any:
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj if len(obj) <= max_str else obj[:max_str] + f"...(+{len(obj) - max_str})"
    if isinstance(obj, dict):
        return {k: _truncate(v, max_str) for k, v in list(obj.items())[:40]}
    if isinstance(obj, list):
        return [_truncate(v, max_str) for v in obj[:40]]
    return obj


def _serialize_run_raw(run) -> dict:
    """尽量完整序列化（供单条深挖）。"""
    if hasattr(run, "dict"):
        data = run.dict()
    elif hasattr(run, "model_dump"):
        data = run.model_dump()
    else:
        return _run_to_dict(run)
    return json.loads(json.dumps(data, default=str))


def export_traces(
    *,
    project: str,
    limit: int,
    days: float | None,
    run_id: str | None,
    name_filter: str | None,
    with_children: bool,
    include_io: bool,
    out_dir: Path,
) -> Path:
    client = Client()
    out_dir.mkdir(parents=True, exist_ok=True)

    start_time = None
    if days is not None and days > 0:
        start_time = datetime.now(timezone.utc) - timedelta(days=days)

    traces: list[dict] = []
    latency_by_name: dict[str, list[float]] = defaultdict(list)

    if run_id:
        root = client.read_run(run_id)
        roots = [root]
    else:
        kwargs: dict[str, Any] = {
            "project_name": project,
            "is_root": True,
            "limit": limit,
        }
        if start_time is not None:
            kwargs["start_time"] = start_time
        if name_filter:
            # filter 语法：https://docs.langchain.com/langsmith/trace-query-syntax
            kwargs["filter"] = f'eq(name, "{name_filter}")'
        roots = list(client.list_runs(**kwargs))

    for root in roots:
        children_rows: list[dict] = []
        if with_children:
            tid = root.trace_id or root.id
            kids = client.list_runs(project_name=project, trace_id=tid)
            for kid in kids:
                if str(kid.id) == str(root.id):
                    continue
                row = _run_to_dict(kid, include_io=include_io)
                children_rows.append(row)
                if row.get("latency_ms") is not None:
                    latency_by_name[row["name"] or "?"].append(row["latency_ms"])

        root_row = _run_to_dict(root, include_io=include_io)
        if root_row.get("latency_ms") is not None:
            latency_by_name[root_row["name"] or "root"].append(root_row["latency_ms"])

        # 子 span 按耗时排序，方便看瓶颈
        children_rows.sort(key=lambda r: r.get("latency_ms") or 0, reverse=True)
        traces.append(
            {
                "root": root_row,
                "children": children_rows,
                "child_count": len(children_rows),
                "slowest_child": children_rows[0] if children_rows else None,
            }
        )

        # 单条完整 dump（可选深挖）
        if run_id:
            (out_dir / f"run_{root.id}.full.json").write_text(
                json.dumps(_serialize_run_raw(root), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # 延迟汇总
    name_stats = []
    for name, vals in sorted(
        latency_by_name.items(), key=lambda kv: -sum(kv[1]) / max(len(kv[1]), 1)
    ):
        vals_sorted = sorted(vals)
        name_stats.append(
            {
                "name": name,
                "count": len(vals),
                "avg_ms": round(sum(vals) / len(vals), 1),
                "p50_ms": vals_sorted[len(vals_sorted) // 2],
                "max_ms": vals_sorted[-1],
                "min_ms": vals_sorted[0],
            }
        )

    summary = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "limit": limit,
        "days": days,
        "run_id": run_id,
        "name_filter": name_filter,
        "with_children": with_children,
        "trace_count": len(traces),
        "latency_by_name": name_stats,
        "traces_preview": [
            {
                "id": t["root"]["id"],
                "name": t["root"]["name"],
                "latency_ms": t["root"]["latency_ms"],
                "error": t["root"]["error"],
                "slowest_child": (
                    {
                        "name": t["slowest_child"]["name"],
                        "latency_ms": t["slowest_child"]["latency_ms"],
                    }
                    if t["slowest_child"]
                    else None
                ),
            }
            for t in traces
        ],
    }

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / "traces.jsonl").open("w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    # 便于直接打开看的精简表
    (out_dir / "latency_by_name.json").write_text(
        json.dumps(name_stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return out_dir


def main() -> None:
    project = os.getenv("LANGSMITH_PROJECT") or "langchain-learn"
    parser = argparse.ArgumentParser(description="导出 LangSmith traces 到本地")
    parser.add_argument("--project", default=project, help="LangSmith project 名")
    parser.add_argument("--limit", type=int, default=20, help="最多导出多少条根 trace")
    parser.add_argument("--days", type=float, default=3, help="只导出最近 N 天（0=不限）")
    parser.add_argument("--run-id", default=None, help="只导出指定 root/run id")
    parser.add_argument("--name", default=None, help='按根 run 名称过滤，如 ChatOpenAI')
    parser.add_argument(
        "--no-children",
        action="store_true",
        help="不拉取子 span（更快，但看不到 model/tool 拆分）",
    )
    parser.add_argument(
        "--no-io",
        action="store_true",
        help="不导出 inputs/outputs（文件更小，只看耗时）",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="输出目录（默认 traces/<时间戳>）",
    )
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or (TRACES_DIR / stamp)
    days = None if args.days == 0 else args.days

    print(f"项目: {args.project}")
    print(f"导出中 → {out_dir}")
    path = export_traces(
        project=args.project,
        limit=args.limit,
        days=days,
        run_id=args.run_id,
        name_filter=args.name,
        with_children=not args.no_children,
        include_io=not args.no_io,
        out_dir=out_dir,
    )
    summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    print(f"完成: {summary['trace_count']} 条 trace")
    print(f"  summary:          {path / 'summary.json'}")
    print(f"  traces.jsonl:     {path / 'traces.jsonl'}")
    print(f"  latency_by_name:  {path / 'latency_by_name.json'}")
    if summary.get("latency_by_name"):
        print("\n耗时 Top（按平均）:")
        for row in summary["latency_by_name"][:8]:
            print(
                f"  {row['avg_ms']:>8.0f} ms avg | "
                f"max {row['max_ms']:.0f} | n={row['count']} | {row['name']}"
            )


if __name__ == "__main__":
    main()
