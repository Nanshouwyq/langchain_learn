# Python 基础速览（Python_basics）

**标签**: Python, 基础

Python 是一门强调可读性的通用编程语言，也是机器学习、数据分析与 LLM 应用（LangChain / LlamaIndex）的主流语言。本文按「语法—数据结构—函数—模块—常用实践」整理，便于笔记检索与复习。

---

## 一、它是什么、适合做什么

| 概念 | 英文 | 说明 |
|------|------|------|
| Python | Python | 解释型、动态类型、跨平台的高级语言 |
| 解释器 | Interpreter | 逐行执行源码（如 CPython） |
| 虚拟环境 | Virtual Environment | 隔离项目依赖（venv / uv / conda） |
| 包管理 | Package Manager | pip、uv、poetry 等安装第三方库 |
| 脚本 / 模块 | Script / Module | `.py` 文件既可直接运行，也可被 import |

**常见用途：** 数据处理、Web、自动化、机器学习、调用 LLM API、写 RAG / Agent。

---

## 二、基本语法与类型

| 概念 | 说明 | 示例形态 |
|------|------|----------|
| 变量 | 名称绑定到对象，无需先声明类型 | `x = 1` |
| 注释 | `#` 单行；`"""..."""` 常作文档字符串 | `# 说明` |
| 缩进 | 用缩进表示代码块（通常 4 空格） | `if` / `for` 下属语句 |
| 整数 / 浮点 | `int` / `float` | `3`、`3.14` |
| 布尔 | `True` / `False` | 条件判断 |
| 字符串 | `str`，可用 f-string 格式化 | `f"hi {name}"` |
| 空值 | `None` 表示「没有值」 | 默认返回值常见 |
| 类型注解 | 标注预期类型，便于阅读与工具检查 | `def f(x: int) -> str:` |

**常用运算符：** 算术 `+ - * / // % **`；比较 `== != < >`；逻辑 `and or not`；成员 `in`；身份 `is`。

---

## 三、控制流

| 结构 | 英文 | 作用 |
|------|------|------|
| 条件 | `if / elif / else` | 按条件分支 |
| 循环 | `for` | 遍历可迭代对象 |
| 循环 | `while` | 条件为真时重复 |
| 跳转 | `break` / `continue` | 结束循环 / 进入下一轮 |
| 占位 | `pass` | 空语句占位 |
| 推导式 | Comprehension | 简洁生成列表/字典/集合 |

```text
for item in items:
    if cond:
        ...
    else:
        ...
```

---

## 四、核心数据结构

| 类型 | 英文 | 特点 | 典型用途 |
|------|------|------|----------|
| 列表 | `list` | 有序、可变、可重复 | 序列处理 `[1, 2, 3]` |
| 元组 | `tuple` | 有序、不可变 | 固定一组值、字典键的一部分 |
| 字典 | `dict` | 键值映射，键唯一 | 配置、JSON 对象、metadata |
| 集合 | `set` | 无序、元素唯一 | 去重、集合运算 |
| 字符串 | `str` | 不可变字符序列 | 文本处理 |

**高频操作：**

| 操作 | 例子 |
|------|------|
| 索引 / 切片 | `a[0]`、`a[1:3]`、`a[-1]` |
| 增删 | `append`、`pop`、`del d[k]` |
| 字典取值 | `d["k"]`、`d.get("k", default)` |
| 解包 | `a, b = (1, 2)` |
| 合并字典 | `{**d1, **d2}`（3.5+）或 `|`（3.9+） |

---

## 五、函数与作用域

| 概念 | 英文 | 定义 |
|------|------|------|
| 函数 | Function | 用 `def` 定义的可复用代码块 |
| 参数 | Parameter | 定义时的形参 |
| 实参 | Argument | 调用时传入的值 |
| 默认参数 | Default Argument | `def f(x=1)`，调用可省略 |
| 可变参数 | `*args` / `**kwargs` | 接收任意位置/关键字参数 |
| 返回值 | Return Value | `return`；无 return 则得 `None` |
| 作用域 | Scope | 局部 / 全局；`global` / `nonlocal` 少用慎用 |
| lambda | Lambda | 单表达式匿名函数 |
| 装饰器 | Decorator | `@decorator` 包装函数/类 |

```text
def add(a: int, b: int = 0) -> int:
    return a + b
```

---

## 六、面向对象入门

| 概念 | 英文 | 说明 |
|------|------|------|
| 类 | Class | 对象的蓝图 `class Person:` |
| 实例 | Instance | 由类创建的具体对象 |
| 方法 | Method | 类里的函数，常含 `self` |
| 属性 | Attribute | 对象上的数据 |
| 继承 | Inheritance | 子类复用/扩展父类 |
| 魔法方法 | Dunder Method | 如 `__init__`、`__str__` |

**与本仓库相关：** Pydantic `BaseModel`、LangChain 的 Runnable/Document 都是类的实例与方法调用。

---

## 七、模块、包与导入

| 概念 | 说明 |
|------|------|
| 模块 | 一个 `.py` 文件 |
| 包 | 含 `__init__.py` 的目录（命名空间包也可无） |
| `import x` | 导入模块 |
| `from x import y` | 从模块导入对象 |
| 相对导入 | `from .config import ...`（仅包内有效） |
| `__name__ == "__main__"` | 区分「被导入」与「直接运行」 |
| `sys.path` | 解释器找模块的路径列表 |

**易错点：** 用 Code Runner 直接跑包内文件时，相对导入会失败；需以模块方式运行或调整 `sys.path`。

---

## 八、异常与上下文管理

| 概念 | 英文 | 说明 |
|------|------|------|
| 异常 | Exception | 运行错误对象，如 `ValueError`、`KeyError` |
| 捕获 | `try / except / else / finally` | 处理或清理 |
| 抛出 | `raise` | 主动抛异常 |
| 上下文管理器 | Context Manager | `with open(...) as f:` 自动关闭资源 |

```text
try:
    ...
except KeyError as e:
    ...
finally:
    ...
```

---

## 九、文件、路径与环境

| 概念 | 推荐做法 |
|------|----------|
| 路径 | 优先 `pathlib.Path`，少手写字符串拼接 |
| 读文本 | `Path.read_text(encoding="utf-8")` 或 `open` |
| 写文本 | `Path.write_text(...)` |
| 项目根 | `Path(__file__).resolve().parent` 向上定位 |
| 环境变量 | `os.getenv("KEY")`；配合 `python-dotenv` 读 `.env` |
| 当前工作目录 | `Path.cwd()`，与「文件所在目录」不是一回事 |

---

## 十、常用内置与标准库（速查）

| 模块 / 能力 | 用途 |
|-------------|------|
| `len` / `range` / `enumerate` / `zip` | 遍历与计数 |
| `isinstance` / `type` | 类型判断 |
| `json` | JSON 序列化与解析 |
| `re` | 正则表达式 |
| `datetime` | 日期时间 |
| `collections` | `Counter`、`defaultdict`、`deque` |
| `itertools` | 迭代工具 |
| `typing` / `collections.abc` | 类型标注相关 |
| `subprocess` | 调用外部命令 |
| `logging` | 日志（比到处 `print` 更适合项目） |

---

## 十一、虚拟环境与依赖（实践）

| 步骤 | 说明 |
|------|------|
| 创建环境 | `python -m venv .venv` 或使用 uv |
| 激活 | macOS/Linux: `source .venv/bin/activate` |
| 安装依赖 | `pip install -r requirements.txt` 或 `uv sync` |
| 导出依赖 | `pip freeze` / 项目的 `pyproject.toml` |
| 运行 | `.venv/bin/python script.py` |

**本仓库相关：** 使用 `.venv` 与 `pyproject.toml` 管理 `langchain` 等依赖；系统可能没有 `python` 命令，常用 `python3` 或 venv 内解释器。

---

## 十二、与数据 / LLM 代码相关的 Python 习惯

| 习惯 | 为什么重要 |
|------|------------|
| 字典传参 | Prompt 变量、metadata、invoke 输入常用 `dict` |
| 列表推导 | 快速整理 Document、拼接 context |
| f-string | 拼提示词、日志 |
| `pathlib` | 定位 `notes/`、`chroma_db/`、`.env` |
| 类型注解 | 配合 Pydantic / IDE 减少字段错误 |
| `.strip()` | 清洗用户输入首尾空白 |
| `if __name__ == "__main__"` | 脚本可测可导入 |

---

## 十三、Pythonic 写法对照

| 较别扭 | 更常见 |
|--------|--------|
| 空列表判断用 `len(a)==0` | `if not a:` |
| 字符串用 `+` 狂拼 | f-string 或 `join` |
| 手动 `for` 建列表 | 列表推导式 |
| 忽略异常类型裸 `except:` | 捕获具体异常 |
| 全局满天飞 | 函数参数传递 / 配置模块 |

---

## 十四、易混概念

| 对比 | 区别 |
|------|------|
| `==` vs `is` | 值相等 vs 同一对象 |
| `list` vs `tuple` | 可变 vs 不可变 |
| `append` vs `extend` / `+` | 追加一个元素 vs 拼接序列 |
| 可变默认参数 | 不要写 `def f(a=[])`，改用 `None` 再在函数内创建 |
| 浅拷贝 vs 深拷贝 | `copy()` / 切片 vs `copy.deepcopy` |
| 模块 vs 包 | 单文件 vs 目录集合 |
| 相对导入 vs 绝对导入 | 包内 `.xxx` vs `package.xxx` |

---

## 十五、术语速查

| 中文 | 英文 |
|------|------|
| 解释器 | Interpreter |
| 动态类型 | Dynamically Typed |
| 可迭代对象 | Iterable |
| 迭代器 | Iterator |
| 生成器 | Generator |
| 推导式 | Comprehension |
| 装饰器 | Decorator |
| 上下文管理器 | Context Manager |
| 虚拟环境 | Virtual Environment |
| 依赖 | Dependency |
| 垃圾回收 | Garbage Collection |

---

## 十六、最小练习清单

1. 用 `list` / `dict` 存几条笔记，并按 key 读取  
2. 写函数：输入字符串，返回 `.strip()` 后长度  
3. 用 `pathlib` 列出 `notes/` 下所有 `.md`  
4. 用 `try/except` 安全读取环境变量缺失的情况  
5. 写一个小类或 Pydantic 模型表示「标题 + 内容 + 标签」  

---

## 参考阅读顺序（自学）

1. 变量、类型、控制流  
2. list / dict / str 高频操作  
3. 函数、模块导入、`__main__`  
4. 文件路径与 `.env`  
5. 类与异常（够用即可）  
6. 再进入 NumPy / Pandas 或 LangChain  

> 本文面向笔记检索与复习，强调 Python「写 LLM / RAG 脚本最常用的那部分」，不展开标准库全貌与高阶元编程。
