"""
첫 MCP 서버 - Hello World
가장 단순한 도구 1개 제공
"""
from mcp.server.fastmcp import FastMCP

# MCP 서버 인스턴스 생성
# name은 클라이언트에 보이는 서버 이름
mcp = FastMCP("hello-server")


# 도구 정의 - @mcp.tool() 데코레이터
@mcp.tool()
def say_hello(name: str) -> str:
    """
    이름을 받아서 인사합니다. 

    Args:
        name: 인사할 사람의 이름

    Returns:
        인사 문자열
    """
    return f"안녕하세요, {name}님! MCP 서버에서 인사드려요. "

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """
    두 숫자를 더합니다. 
    
    Args:
        a: 첫 번째 숫자
        b: 두 번째 숫자
        
    Returns:
        두 숫자의 합
    """
    return a + b

# 서버 실행 (stdio 방식)
if __name__ == "__main__":
    mcp.run()