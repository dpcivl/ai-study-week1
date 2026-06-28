"""
MCP의 Tools + Resources 둘 다 활용하는 에이전트
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


# 본인 환경에 맞게 경로 수정
MCP_SERVER_PATH = "C:/dev/ai-study/week1-api-basics/week5-mcp/energy_with_resources.py"
PYTHON_PATH = "C:/dev/ai-study/week1-api-basics/venv/Scripts/python.exe"


mcp_client = MultiServerMCPClient(
    {
        "energy": {
            "command": PYTHON_PATH,
            "args": [MCP_SERVER_PATH],
            "transport": "stdio"
        }
    }
)



class State(TypedDict):
    messages: Annotated[list, add_messages]


async def get_all_resources_content():
    """MCP 서버의 Resources를 미리 가져와서 시스템 프롬프트에 포함"""
    async with mcp_client.session("energy") as session:
        # 사용 가능한 리소스 목록
        resources_list = await session.list_resources()

        resources_content = []
        for resource in resources_list.resources:
            # 각 리소스 내용 읽기
            result = await session.read_resource(resource.uri)

            content_text = ""
            for content in result.contents:
                if hasattr(content, 'text'):
                    content_text = content.text
                    break

            resources_content.append({
                "uri": str(resource.uri),
                "name": resource.name,
                "content": content_text
            })

        return resources_content
    

async def main():
    # 1. Resources 미리 가져오기
    print("Resources 가져오는 중...")
    resources = await get_all_resources_content()
    print(f"{len(resources)}개 Resource 로드:")
    for r in resources:
        print(f"  - {r['uri']}: {len(r['content'])}자")

    # 2. Tools 가져오기
    print("\nTools 가져오는 중...")
    tools = await mcp_client.get_tools()
    print(f"{len(tools)}개 Tool 로드")

    # 3. Resources를 시스템 프롬프트로 구성
    resources_text = "\n\n=== 참고 자료 ===\n"
    for r in resources:
        resources_text += f"\n[{r['name']}]\n{r['content']}\n"

    system_content = f"""당신은 공장 에너지 관리 전문 에이전트입니다. 

다음 참고 자료를 항상 활용해서 답변하세요. 
도구로 데이터 조회 후, 참고 자료의 규정과 가이드를 적용해서 분석하세요. 

{resources_text}

답변 규칙:
- 데이터 조회는 적절한 도구 사용
- 규정 위반 여부 항상 체크
- 트러블슈팅 가이드 참고
- 한국어로 명확하게 """
    
    # 4. LLM 셋업
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=0
    ).bind_tools(tools)

    def call_llm(state: State):
        response = llm.invoke([SystemMessage(content=system_content)] + state["messages"])
        return {"messages": [response]}
    
    async def execute_tools(state: State):
        last_message = state["messages"][-1]
        tool_results = []

        for tool_call in last_message.tool_calls:
            print(f"\n[도구 호출 {tool_call['name']}({tool_call['args']})]")
            for t in tools:
                if t.name == tool_call["name"]:
                    result = await t.ainvoke(tool_call["args"])
                    print(f"[결과] {str(result)[:150]}...")
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

    # 5. 풍부한 질문 (Resources 활용 필요)
    question = (
        "line_4의 최근 24시간 전력 사용량 보고, "
        "운영 규정 위반 여부 확인해줘. "
        "위반이면 어떻게 대응해야 하는지도 알려줘."
    )

    print("\n" + "=" * 70)
    print(f"질문: {question}")
    print("=" * 70)

    initial = {"messages" : [HumanMessage(content=question)]}
    result = await app.ainvoke(initial)

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