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


# ===== 확장된 State =====
class AgentState(TypedDict):
    # 대화 히스토리 (add_messages reducer)
    messages: Annotated[list, add_messages]
    
    # 추가 정보들
    user_name: str           # 사용자 이름
    session_start: str       # 세션 시작 시간
    tool_call_count: int     # 도구 호출 횟수 (제한용)
    last_search_query: str   # 마지막 검색어 (디버깅용)


# ===== 도구 정의 =====
@tool
def calculator(operation: str, a: float, b: float) -> str:
    """사칙연산을 수행합니다. operation은 add, subtract, multiply, divide 중 하나."""
    if operation == "add":
        return f"{a} + {b} = {a + b}"
    elif operation == "subtract":
        return f"{a} - {b} = {a - b}"
    elif operation == "multiply":
        return f"{a} * {b} = {a * b}"
    elif operation == "divide":
        if b == 0:
            return "0으로 나눌 수 없습니다"
        return f"{a} / {b} = {a / b}"


@tool
def get_current_time() -> str:
    """현재 시간을 한국 시간으로 반환합니다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


tools = [calculator, get_current_time]


# ===== LLM =====
llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0
).bind_tools(tools)


# ===== 노드 함수들 =====

def initialize(state: AgentState):
    """초기화 노드 - 세션 시작"""
    print(f"\n[initialize] 세션 시작")
    
    return {
        "session_start": datetime.now().strftime("%H:%M:%S"),
        "tool_call_count": 0,
        "last_search_query": ""
    }


def call_llm(state: AgentState):
    """LLM 호출 - State 활용한 시스템 프롬프트"""
    print(f"\n[call_llm] 도구 호출 횟수: {state.get('tool_call_count', 0)}")
    
    # 시스템 프롬프트에 State 정보 활용
    system_content = f"""당신은 친근한 학습 도우미입니다.

현재 사용자: {state.get('user_name', '익명')}
세션 시작: {state.get('session_start', '알 수 없음')}
지금까지 도구 호출: {state.get('tool_call_count', 0)}회

규칙:
- 정확한 계산은 calculator 도구 사용
- 시간/날짜 질문은 get_current_time 도구 사용
- 한국어로 친근하게 답변
- 사용자 이름을 자연스럽게 호명"""

    # SystemMessage + 기존 messages
    messages_with_system = [SystemMessage(content=system_content)] + state["messages"]
    
    response = llm.invoke(messages_with_system)
    
    return {"messages": [response]}


def execute_tools(state: AgentState):
    """도구 실행 + 카운트 증가"""
    last_message = state["messages"][-1]
    
    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        print(f"  도구 호출: {tool_name}({tool_args})")
        
        for t in tools:
            if t.name == tool_name:
                result = t.invoke(tool_args)
                print(f"  결과: {result}")
                tool_results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
                break
    
    # State 업데이트: messages + 카운트 증가
    return {
        "messages": tool_results,
        "tool_call_count": state.get("tool_call_count", 0) + len(tool_results)
    }


def should_continue(state: AgentState):
    """다음 노드 결정"""
    last_message = state["messages"][-1]
    
    # 도구 호출 횟수 제한 (안전장치)
    if state.get("tool_call_count", 0) >= 10:
        print(f"\n[안전장치] 도구 호출 10회 초과, 종료")
        return "end"
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return "end"


# ===== 그래프 빌드 =====
workflow = StateGraph(AgentState)

workflow.add_node("initialize", initialize)
workflow.add_node("call_llm", call_llm)
workflow.add_node("execute_tools", execute_tools)

# 시작: initialize → call_llm
workflow.set_entry_point("initialize")
workflow.add_edge("initialize", "call_llm")

# 분기
workflow.add_conditional_edges(
    "call_llm",
    should_continue,
    {
        "execute_tools": "execute_tools",
        "end": END
    }
)

# 루프
workflow.add_edge("execute_tools", "call_llm")

app = workflow.compile()


# ===== 실행 =====
def run(question: str, user_name: str = "학습자"):
    print("=" * 70)
    print(f"질문: {question}")
    print(f"사용자: {user_name}")
    print("=" * 70)
    
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "user_name": user_name,
        "session_start": "",
        "tool_call_count": 0,
        "last_search_query": ""
    }
    
    final_state = app.invoke(initial_state)
    
    # 최종 답변 출력
    final_message = final_state["messages"][-1]
    print(f"\n[최종 답변]")
    if isinstance(final_message.content, str):
        print(final_message.content)
    else:
        for block in final_message.content:
            if isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text", ""))
    
    # State 정보 출력 (확인용)
    print(f"\n[세션 통계]")
    print(f"  세션 시작: {final_state.get('session_start')}")
    print(f"  도구 호출 횟수: {final_state.get('tool_call_count')}")
    print(f"  총 메시지 수: {len(final_state['messages'])}")


if __name__ == "__main__":
    run("847 곱하기 2391은?", user_name="철수")
    print("\n")
    run("지금 몇 시야? 그리고 100을 7로 나누면 얼마?", user_name="영희")