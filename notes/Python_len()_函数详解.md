# Python `len()` 函数详解

**标签**: Python, 基础

`len()` 是 Python 最常用的内置函数之一，用于返回对象的「长度」或「元素个数」。本文按定义、适用类型、原理、易错点与实践整理，便于笔记检索。

---

## 一、是什么

| 项目 | 说明 |
|------|------|
| 函数名 | `len` |
| 类型 | 内置函数（Built-in Function） |
| 作用 | 返回容器或序列中元素的数量 |
| 返回类型 | `int`（非负整数） |
| 时间复杂度 | 对内置容器通常是 **O(1)**（长度被缓存） |

```python
len("hello")      # 5
len([1, 2, 3])    # 3
len({"a": 1})     # 1
```

---

## 二、函数签名与定义

```text
len(s)
```

| 参数 | 含义 |
|------|------|
| `s` | 支持长度协议的对象（实现了 `__len__`） |

等价理解：`len(obj)` ≈ 调用 `obj.__len__()`，再把结果转成整数返回。

---

## 三、可以对哪些对象使用

| 类型 | 英文 | `len` 返回什么 | 示例 |
|------|------|----------------|------|
| 字符串 | `str` | 字符个数 | `len("你好")` → `2` |
| 列表 | `list` | 元素个数 | `len([1, 2])` → `2` |
| 元组 | `tuple` | 元素个数 | `len((1,))` → `1` |
| 字典 | `dict` | **键** 的个数 | `len({"a": 1, "b": 2})` → `2` |
| 集合 | `set` / `frozenset` | 元素个数 | `len({1, 1, 2})` → `2` |
| 字节 | `bytes` / `bytearray` | 字节数 | `len(b"ab")` → `2` |
| range | `range` | 区间长度 | `len(range(5))` → `5` |

**注意：** 普通整数、浮点数、`None`、未实现 `__len__` 的对象不能用 `len()`。

```python
len(100)     # TypeError: object of type 'int' has no len()
len(None)    # TypeError
```

---

## 四、底层协议：`__len__`

| 概念 | 说明 |
|------|------|
| `__len__` | 对象定义「长度」的魔法方法 |
| 返回要求 | 应返回 `>= 0` 的整数 |
| 布尔关系 | 若对象同时没有 `__bool__`，则 `bool(obj)` 常等价于 `len(obj) != 0` |

自定义类示例：

```python
class Team:
    def __init__(self, members):
        self.members = members

    def __len__(self):
        return len(self.members)

len(Team(["a", "b"]))  # 2
```

若 `__len__` 返回负数，Python 会报错（`ValueError`）。

---

## 五、常见用法场景

### 1. 判断是否为空

```python
if len(items) == 0:
    ...
```

更 Pythonic 的写法（通常推荐）：

```python
if not items:
    ...
```

### 2. 遍历前预知大小

```python
n = len(rows)
for i in range(n):
    ...
```

很多情况可直接 `for x in rows:`，不必先 `len`。

### 3. 校验输入

```python
if len(password) < 8:
    raise ValueError("密码太短")
```

### 4. 处理 LLM / RAG 文本

```python
text = user_input.strip()
print(len(text))  # 清洗后的字符数，可用于截断或统计
```

### 5. 统计字典 / metadata 字段数

```python
meta = {"category": "编程", "source": "notes/a.md"}
len(meta)  # 2 个键
```

---

## 六、字符串相关细节

| 情况 | 结果要点 |
|------|----------|
| 英文 | 按字符计，`'abc'` → 3 |
| 中文 | 按 Unicode 字符计，`'机器学习'` → 4 |
| 空串 | `len("")` → `0` |
| 含空格 | 空格也算字符，`len("a b")` → 3 |
| 换行符 | `\n` 算 1 个字符 |
| emoji | 多数单个 emoji 长度为 1；含组合字符时可能 > 1 |

```python
len("🐍")          # 通常为 1
len("a\nb")        # 3
len("  hi  ".strip())  # 2
```

**和「字节长度」区分：**

```python
s = "中"
len(s)                 # 1 个字符
len(s.encode("utf-8")) # 3 个字节
```

---

## 七、列表 / 字典易错点

| 易错点 | 说明 |
|--------|------|
| 嵌套列表 | `len([[1, 2], [3]])` → `2`（外层元素数，不是全部数字个数） |
| 字典长度 | 是键数量，不是「键+值」总数 |
| 视图对象 | `len(d.keys())`、`len(d.values())` 与 `len(d)` 相同 |
| 生成器 | **不能**直接 `len(generator)` |

```python
len(x for x in range(3))   # TypeError
len([x for x in range(3)]) # 3，列表可以
```

若必须知道生成器「有多长」，需先物化为 list（会耗内存），或自己计数遍历。

---

## 八、性能要点

| 对象 | `len()` 复杂度 | 原因 |
|------|----------------|------|
| list / tuple / dict / set / str | O(1) | 长度信息已维护 |
| 自定义 `__len__` | 取决于你的实现 | 可能是 O(n) |
| 自己手写循环计数 | O(n) | 一般不如内置 `len` |

结论：对内置容器，放心用 `len()`，不必自己循环数。

---

## 九、与相关函数 / 写法对比

| 写法 | 含义 |
|------|------|
| `len(x)` | 元素个数 |
| `x.__len__()` | 直接调协议方法（一般不推荐手写） |
| `sum(1 for _ in x)` | 可迭代对象计数（生成器可用，但 O(n)） |
| `sys.getsizeof(x)` | 对象内存占用（字节），**不是**元素个数 |
| `len(s.encode())` | 编码后字节数，不是字符数 |

---

## 十、布尔语境与空值判断

| 表达式 | 常见含义 |
|--------|----------|
| `if len(x):` | 非空为真 |
| `if len(x) == 0:` | 为空 |
| `if x:` | 对容器通常等价「非空」，更简洁 |
| `if x is None:` | 判断是否为 `None`，与长度无关 |

```python
x = []
bool(x)       # False
len(x) == 0   # True
```

---

## 十一、异常速查

| 报错 | 常见原因 |
|------|----------|
| `TypeError: object of type 'X' has no len()` | X 不支持长度协议 |
| `ValueError: __len__() should return >= 0` | 自定义 `__len__` 返回了负数 |
| `TypeError`（生成器） | 对 generator / iterator 直接 `len` |

---

## 十二、实践清单（可对照练习）

1. 对 `str` / `list` / `dict` / `set` 各测一次 `len`  
2. 比较 `len("中文")` 与 `len("中文".encode("utf-8"))`  
3. 对嵌套列表确认 `len` 只看最外层  
4. 自定义一个带 `__len__` 的类并调用 `len`  
5. 尝试对生成器 `len(...)`，观察报错后改用 `list` 或计数循环  

---

## 十三、术语速查

| 中文 | 英文 |
|------|------|
| 内置函数 | Built-in Function |
| 长度协议 | Length Protocol |
| 魔法方法 | Dunder Method (`__len__`) |
| 可调整大小的容器 | Sized（`collections.abc.Sized`） |
| 字符 vs 字节 | Character vs Byte |

---

## 十四、一句话总结

> `len(obj)` 返回「对象有多长」：对序列是元素/字符数，对字典是键数；它依赖 `__len__`，对 list/dict/str 等内置类型极快；生成器与数字类型不能直接用。

> 本文面向笔记检索与复习，聚焦日常开发（含文本清洗、校验、RAG 预处理）中的 `len()` 用法。
