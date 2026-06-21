import os
from typing import TypedDict, Annotated
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()


# State (간단한 버전)
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    user_name: str
    session_start: str
    turn_count: int  # 대화 턴 수


# 도구 (간단히)
@tool
def get_current_time() -> str:
    """현재 시간을 한국 시간으로 반환합니다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def calculator(operation: str, a: float, b: float) -> str:
    """사칙연산. operation: add/subtract/multiply/divide"""
    ops = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else "div by zero"
    }
    return f"결과: {ops.get(operation, '알 수 없는 연산')}"


@tool
def remember_fact(fact: str) -> str:
    """사용자가 알려준 중요한 사실을 기억합니다."""
    return f"기억했어요: '{fact}'"


tools = [get_current_time, calculator, remember_fact]


llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0.7  # 챗봇이라 약간 자유롭게
).bind_tools(tools)


def call_llm(state: ChatState):
    system_content = f"""당신은 {state.get('user_name', '사용자')}님의 친근한 대화 도우미입니다.

세션 시작: {state.get('session_start', '')}
현재 턴: {state.get('turn_count', 0)}

규칙:
- 한국어로 자연스럽게
- 이름을 자주 호명
- 필요하면 도구 사용 (시간, 계산, 기억)
- 친근하고 약간 유머러스하게"""

    messages_with_system = [SystemMessage(content=system_content)] + state["messages"]
    response = llm.invoke(messages_with_system)
    return {"messages": [response]}


def execute_tools(state: ChatState):
    last_message = state["messages"][-1]
    
    tool_results = []
    for tool_call in last_message.tool_calls:
        for t in tools:
            if t.name == tool_call["name"]:
                result = t.invoke(tool_call["args"])
                tool_results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
                break
    
    return {"messages": tool_results}


def should_continue(state: ChatState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return "end"


# 그래프
workflow = StateGraph(ChatState)
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


# ===== 대화 모드 =====
def chat_loop(user_name: str):
    """대화 루프 - 상태를 직접 관리하면서 여러 턴 진행"""
    print(f"\n{user_name}님, 안녕하세요! 'quit' 입력 시 종료.\n")
    
    # 대화 히스토리 직접 관리
    session_state = {
        "messages": [],
        "user_name": user_name,
        "session_start": datetime.now().strftime("%H:%M:%S"),
        "turn_count": 0
    }
    
    while True:
        user_input = input(f"{user_name}: ")
        
        if user_input.lower() in ["quit", "exit", "종료"]:
            print(f"\n안녕히 가세요, {user_name}님!")
            break
        
        # 턴 카운트
        session_state["turn_count"] += 1
        
        # 사용자 메시지 추가
        session_state["messages"].append(HumanMessage(content=user_input))
        
        # 에이전트 호출
        result = app.invoke(session_state)
        
        # State 업데이트 (다음 턴 위해)
        session_state["messages"] = result["messages"]
        
        # 답변 출력
        final_message = result["messages"][-1]
        print(f"\nAI: ", end="")
        if isinstance(final_message.content, str):
            print(final_message.content)
        else:
            for block in final_message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    print(block.get("text", ""))
        print()


if __name__ == "__main__":
    chat_loop("박효인")  # 본인 이름으로 변경