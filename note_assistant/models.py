from pydantic import BaseModel, Field


# 创建笔记数据模型
class NoteCreate(BaseModel):
    title: str = Field(description="笔记标题")
    content: str = Field(description="笔记内容")
    tags: list[str] = Field(default_factory=list, description="笔记标签")
