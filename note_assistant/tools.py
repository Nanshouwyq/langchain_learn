"""工具模块，提供一些工具函数"""

from langchain_core.messages.utils import filter_messages
from langchain_core.tools import tool
from .models import NoteCreate
from pathlib import Path
from .config import NOTES_DIR
from .chains import rebuild_vectorstore, ask_notes


def _note_path(title: str) -> Path:
    """获取笔记路径"""
    fileName = f"{title.replace(' ', '_')}.md"
    return NOTES_DIR / fileName


def _refresh_knowledge_base() -> str:
    try:
        rebuild_vectorstore()
    except Exception as e:
        return f"重建知识库失败: {e}"
    return "知识库重建成功"


# 创建笔记
@tool
def create_note(title: str, content: str, tags: str) -> str:
    """创建笔记"""
    # 拆分tags 为列表
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    # 创建笔记
    note = NoteCreate(title=title.strip(), content=content.strip(), tags=tag_list)
    filePath = _note_path(title)
    if filePath.exists():
        return f"笔记已存在: {note.title}, 请使用其他标题或者更新笔记"
    # 写标题
    note_content = f"# {note.title}\n\n"
    if note.tags:
        note_content += f"**标签**: {', '.join(note.tags)}\n\n"
    note_content += f"{note.content}\n"
    filePath.write_text(note_content, encoding="utf-8")
    return f"笔记创建成功: {note.title}\n {_refresh_knowledge_base()}"


# 列出所有笔记
@tool
def list_notes(tag: str = "") -> str:
    """列出所有笔记，可按标签过滤"""
    note_paths = sorted(NOTES_DIR.rglob("*.md"))
    if not note_paths:
        return "没有笔记,先创建"
    filter_tag = tag.strip()
    if filter_tag:
        filtered_paths = []
        for note_path in note_paths:
            note_content = note_path.read_text(encoding="utf-8")
            if filter_tag in note_content and "**标签**" in note_content:
                filtered_paths.append(note_path)
        note_paths = filtered_paths
        if not note_paths:
            return f"没有找到包含标签: {filter_tag} 的笔记"

    lines = [f"共找到{len(note_paths)}篇笔记："]
    for index, note_path in enumerate(note_paths, start=1):
        lines.append(f"{index}. {note_path.stem.replace('_', ' ')}")
    return "\n".join(lines)


# 更新笔记
@tool
def update_note(title: str, content: str) -> str:
    """更新笔记"""
    filePath = _note_path(title.strip())
    if not filePath.exists():
        return f"笔记不存在: {title},无法更新"

    old_content = filePath.read_text(encoding="utf-8")
    lines = old_content.splitlines()

    new_content = lines[0] + "\n\n"
    if len(lines) > 2 and lines[2].startswith("**标签**:"):
        new_content += lines[2] + "\n\n"
    new_content += content.strip() + "\n"
    filePath.write_text(new_content, encoding="utf-8")
    return f"笔记更新成功: {title}\n {_refresh_knowledge_base()}"


# 删除笔记
@tool
def delete_note(title: str) -> str:
    """删除笔记"""
    filePath = _note_path(title.strip())
    if not filePath.exists():
        return f"笔记不存在: {title},无法删除"
    filePath.unlink()
    return f"笔记删除成功: {title}\n {_refresh_knowledge_base()}"


# 问题
@tool
def answer_from_notes(question: str) -> str:
    """回答问题"""
    return ask_notes(question.strip())


ALL_TOOLS = [create_note, list_notes, update_note, delete_note, answer_from_notes]
# if __name__ == "__main__":
#     # print(list_notes.invoke({"tag": ""}))
#     # 测试创建笔记
#     print(
#         create_note.invoke(
#             {"title": "测试笔记", "content": "这是测试笔记的内容", "tags": "测试,笔记"}
#         )
#     )

#     print(
#         update_note.invoke(
#             {"title": "测试笔记", "content": "这是更新后的测试笔记的内容"}
#         )
#     )

#     print(delete_note.invoke({"title": "测试笔记"}))
