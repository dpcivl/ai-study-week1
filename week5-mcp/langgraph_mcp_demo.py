"""
LangGraph 에이전트가 MCP 서버를 호출
어제 만든 MCP 서버를 본인 코드에서 사용
"""
import asyncio
from typing import TypedDict, Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()


# ===== MCP 클라이언트 셋업 =====
# 본인 MCP 서버 경로 (절대 경로 사용)
MCP_SERVER_PATH = "C:/dev/ai-study/week1-api-basics/week5-mcp/energy_with_resources.py"
PYTHON_PATH = "c:/dev/ai-study/week1-api-basics/venv/Scripts/python.exe"

# 본인 환경에 맞게 경로 수정 필요

mcp_client = MultiServerMCPClient(
    {
        "energy": {
            "command": PYTHON_PATH,
            "args": [MCP_SERVER_PATH],
            "transport": "stdio"
        }
    }
)


# ===== State =====
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ===== 메인 로직 =====
async def main():
    # MCP 서버에서 도구 가져오기
    print("MCP 서버 연결 중...")
    tools = await mcp_client.get_tools()
    print(f"MCP 도구 {len(tools)}개 로드 완료:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")

    # LLM 준비
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0
    ).bind_tools(tools)

    # 노드 함수들
    def call_llm(state: State):
        system_msg = SystemMessage(
            content="당신은 공장 에너지 관리 에이전트입니다. "
            "MCP 도구를 활용해서 사용자 질문에 답하세요."
        )
        response = llm.invoke([system_msg] + state["messages"])
        return {"messages": [response]}
    
    async def execute_tools(state: State):
        last_message = state["messages"][-1]

        tool_results = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"\n[MCP 도구 호출] {tool_name}({tool_args})")

            # MCP 도구 찾기 + 실행
            for t in tools:
                if t.name == tool_name:
                    result = await t.ainvoke(tool_args)
                    print(f"[결과] {str(result)[:200]}...")
                    tool_results.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"]
                    ))
                    break

        return {"messages": tool_results}
    
    def should_continue(state: State):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "execute_tools"
        return "end"
    
    # 그래프 
    workflow = StateGraph(State)
    workflow.add_node("call_llm", call_llm)
    workflow.add_node("execute_tools", execute_tools)

    workflow.set_entry_point("call_llm")
    workflow.add_conditional_edges(
        "call_llm",
        should_continue,
        {"execute_tools": "execute_tools", "end": END}
    )
    workflow.add_edge("execute_tools", "call_llm")

    app = workflow.compile()

    # 테스트
    test_questions = [
        "공장 라인 목록 보여줘",
        "line_4의 최근 12시간 전력 사용량 분석해줘",
    ]

    for question in test_questions:
        print("\n" + "=" * 70)
        print(f"질문: {question}")
        print("=" * 70)

        initial = {"messages": [HumanMessage(content=question)]}
        result = await app.ainvoke(initial)

        # 최종 답변
        final_message = result["messages"][-1]
        print(f"\n[최종 답변]")
        if isinstance(final_message.content, str):
            print(final_message.content)
        else:
            for block in final_message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    print(block.get("text", ""))


if __name__ == "__main__":
    asyncio.run(main())