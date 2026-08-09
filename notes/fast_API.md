# fast API

**标签**: FastAPI, python, backend

# FastAPI
FastAPI 是基于 **Python** 的高性能 Web 框架，专门用来写接口（REST API），现代、开发效率高，现在AI后端、RAG服务、模型封装非常常用。

> 底层：Starlette（异步web）+ Pydantic（数据校验）

## 核心优点
1. **自动接口文档**：写完代码自动生成 Swagger UI `/docs`、ReDoc `/redoc`
2. **类型提示**：利用 Python type hint，自动做请求参数校验、解析
3. **原生异步 async/await**，也支持普通同步函数
4. 性能高，接近 Node、Go；
5. Pydantic 自动做请求体、查询参数校验，出错直接返回友好错误信息

## 最小示例
### 1.安装
```bash
pip install fastapi uvicorn
```
uvicorn 是ASGI服务器，用来运行FastAPI。

### main.py
```python
from fastapi import FastAPI

app = FastAPI(title="Demo接口服务")

# get接口
@app.get("/hello")
def hello(name: str = "world"):
    return {"msg": f"hello {name}"}

# post接口，接收json
from pydantic import BaseModel

class User(BaseModel):
    username: str
    age: int

@app.post("/user")
def create_user(user: User):
    return {"user": user.dict()}
```

### 启动服务
```bash
uvicorn main:app --reload
```
- `main`：文件名 main.py
- `app`：代码里 `app = FastAPI()` 的实例
- `--reload`：开发模式，改代码自动重启，生产不要开

访问：
- 接口：`http://127.0.0.1:8000/hello`
- **交互式文档**：`http://127.0.0.1:8000/docs` ✨最常用，可以直接在页面调试接口

## 常用知识点速览
### 1.参数类型
- **路径参数** `/item/{item_id}`
```python
@app.get("/item/{item_id}")
def read_item(item_id:int):
    return {"id":item_id}
```
- **查询参数** `/items?limit=10`
函数普通入参就是查询参数
- **请求体Body**：用Pydantic BaseModel（POST JSON）
- **Header / Cookie / Form 表单**：`from fastapi import Header, Cookie, Form`

### 2.异步写法
函数加上 `async def`
```python
@app.get("/async-demo")
async def demo():
    return {"ok":True}
```
> 同步函数def FastAPI也会自动放到线程池运行，不用全部改成async。

### 3.返回自定义状态码、异常
```python
from fastapi import HTTPException

@app.get("/error")
def err():
    raise HTTPException(status_code=404, detail="资源不存在")
```

### 4.跨域CORS（前端调用必配）
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #生产不要写*，写前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 实际AI场景使用
经常用来封装大模型、RAG服务，把LangChain/LlamaIndex包装成http接口给前端调用。
```python
#伪代码示例
@app.post("/rag/chat")
def rag_chat(query:str):
    resp = rag_chain.invoke(query)
    return {"answer":resp}
```

## 生产部署注意
1. 关闭 `--reload`
2. uvicorn 多工作进程：`uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000`
3. 前面可套 Nginx；也可以用 gunicorn + uvicorn workers
4. Pydantic v2 现在FastAPI默认使用，注意版本兼容

## 和其他框架简单对比
|框架|特点|
|---|---|
|FastAPI|异步、自动文档、类型校验，接口首选|
|Flask|轻量同步，无自动校验，老项目多|
|Django|大而全，ORM后台admin，适合完整网站|

如果你需要，我可以给你：
1. FastAPI + RAG完整最小可运行demo
2. 项目目录分层模板（routers路由拆分、依赖注入）
3. Dockerfile打包FastAPI示例
4. 高频面试题整理

你想要哪个？
