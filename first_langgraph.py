import os
from typing import TypedDict, Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()

# ===== 1. 도구 정의 =====
@tool
def calculator(operation: str, a: float, b: float) -> float:
    """사칙연산을 수행합니다. operation은 add, subtract, multiply, divide 중 하나."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a / b if b != 0 else "division by zero"
    
@tool
def get_weather(city: str) -> str:
    """도시의 현재 날씨를 조회합니다."""
    weather_db = {"부산": "맑음, 22도", "서울": "흐림, 18도"}
    return weather_db.get(city, f"{city}: 정보 없음")

tools = [calculator, get_weather]


# ===== 2. State 정의 =====
class AgentState(TypedDict):
    # add_messages: 메시지를 누적 추가하는 특별한 reducer
    messages: Annotated[list, add_messages]


# ===== 3. LLM 준비 =====
llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0
).bind_tools(tools)


# ===== 4. 노드 함수들 =====
def call_llm(state: AgentState):
    """LLM 호출 노드"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def execute_tools(state: AgentState):
    """도구 실행 노드"""
    last_message = state["messages"][-1]

    tool_results = []
    for tool_call in last_message.tool_calls:
        # 도구 이름으로 실제 함수 찾기
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # 도구 실행
        for t in tools:
            if t.name == tool_name:
                result = t.invoke(tool_args)
                tool_results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
                break

    return {"messages": tool_results}


# ===== 5. 라우팅 함수 =====
def should_continue(state: AgentState):
    """다음에 뭐 할지 결정"""
    last_message = state["messages"][-1]

    # 도구 호출이 있으면 -> execute_tools로
    if last_message.tool_calls:
        return "execute_tools"
    # 없으면 -> 종료
    return "end"


# ===== 6. 그래프 빌드 =====
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("call_llm", call_llm)
workflow.add_node("execute_tools", execute_tools)

# 시작점
workflow.set_entry_point("call_llm")

# 조건부 엣지: call_llm 후에 분기
workflow.add_conditional_edges(
    "call_llm",
    should_continue,
    {
        "execute_tools": "execute_tools",
        "end": END
    }
)

# 도구 실행 후엔 항상 call_llm으로 돌아감 (루프)
workflow.add_edge("execute_tools", "call_llm")

# 컴파일
app = workflow.compile()

# ===== 7. 실행 =====
def run(question: str):
    print("=" * 60)
    print(f"질문: {question}")
    print("=" * 60)

    initial_state = {
        "messages": [HumanMessage(content=question)]
    }

    # 실행하면서 각 단계 출력
    for event in app.stream(initial_state):
        for node_name, output in event.items():
            print(f"\n[노드: {node_name}]")
            if "messages" in output:
                for msg in output["messages"]:
                    msg_type = type(msg).__name__
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        print(f"  {msg_type}: 도구 호출 {[tc['name'] for tc in msg.tool_calls]}")
                    elif hasattr(msg, "content"):
                        content = msg.content[:150] if isinstance(msg.content, str) else str(msg.content)[:150]
                        print(f"  {msg_type}: {content}...")
    print()

# 테스트
if __name__ == "__main__":
    run("847 곱하기 2391은?")
    run("부산이랑 서울 날씨 비교해줘")
    run("파이썬에서 리스트 컴프리헨션이 뭐야?")


# first_langgraph.py 끝에 추가
from IPython.display import Image
try:
    png = app.get_graph().draw_mermaid_png()
    with open("agent_graph.png", "wb") as f:
        f.write(png)
    print("그래프 이미지 저장: agent_graph.png")
except Exception as e:
    print(f"이미지 저장 실패 (선택적): {e}")
    # 대신 mermaid 코드만
    print(app.get_graph().draw_mermaid())