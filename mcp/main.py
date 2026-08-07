from fastmcp import FastMCP
import math

# 创建MCP server 实例
mcp = FastMCP("calculator")


# 基础运算工具
@mcp.tool
def add(a: int, b: int) -> int:
    return a + b


@mcp.tool
def subtract(a: int, b: int) -> int:
    return a - b


@mcp.tool
def multiply(a: int, b: int) -> int:
    return a * b


@mcp.tool
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("除数不能为0")
    return a / b


@mcp.tool
def square_root(x: float) -> float:
    return math.sqrt(x)


@mcp.tool
def power(base: float, exponent: float) -> float:
    return base**exponent


if __name__ == "__main__":
    mcp.run()
