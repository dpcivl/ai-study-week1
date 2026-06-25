import os
from typing import TypedDict, Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()


# 가짜 데이터베이스 (실전은 진짜 DB)
FAKE_DB = {
    "user_1": {"name": "철수", "email": "철수@example.com", "score": 100},
    "user_2": {"name": "영희", "email": "영희@example.com", "score": 85},
    "user_3": {"name": "민수", "email": "민수@example.com", "score": 70},
}


# ===== 도구들 =====

# 안전한 도구
@tool
def search_users(name: str) -> str:
    """사용자를 이름으로 검색합니다 (읽기 전용)."""
    results = []
    for user_id, info in FAKE_DB.items():
        if name.lower() in info["name"].lower():
            results.append(f"{user_id}: {info}")
    return "\n".join(results) if results else "검색 결과 없음"


@tool
def get_user_info(user_id: str) -> str:
    """사용자 정보를 조회합니다 (읽기 전용)."""
    if user_id in FAKE_DB:
        return str(FAKE_DB[user_id])
    return f"사용자 {user_id} 없음"


# 위험한 도구 (HITL 필요)
@tool
def update_user_score(user_id: str, new_score: int) -> str:
    """사용자의 점수를 변경합니다. ⚠️ 위험 - 데이터 수정."""
    if user_id not in FAKE_DB:
        return f"사용자 {user_id} 없음"
    
    old_score = FAKE_DB[user_id]["score"]
    FAKE_DB[user_id]["score"] = new_score
    return f"점수 변경 완료: {user_id} {old_score} → {new_score}"


@tool
def delete_user(user_id: str) -> str:
    """사용자를 삭제합니다. ⚠️ 위험 - 영구 삭제."""
    if user_id not in FAKE_DB:
        return f"사용자 {user_id} 없음"
    
    deleted = FAKE_DB.pop(user_id)
    return f"사용자 삭제 완료: {deleted}"


# 위험한 도구 목록 (HITL 적용 대상)
DANGEROUS_TOOLS = {"update_user_score", "delete_user"}

tools = [search_users, get_user_info, update_user_score, delete_user]


# ===== State =====
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ===== LLM =====
llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0
).bind_tools(tools)


def call_llm(state: State):
    system_content = """당신은 사용자 데이터 관리 에이전트입니다.

도구:
- search_users: 이름으로 사용자 검색
- get_user_info: 사용자 정보 조회
- update_user_score: 사용자 점수 변경 (⚠️ 위험)
- delete_user: 사용자 삭제 (⚠️ 위험)

규칙:
- 위험 도구는 반드시 명확한 의도 확인 후 호출
- 사용자 ID 정확히 알고 있을 때만 수정/삭제
- 한국어로 자연스럽게 응답"""

    response = llm.invoke([SystemMessage(content=system_content)] + state["messages"])
    return {"messages": [response]}


def execute_tools(state: State):
    """도구 실행"""
    last_message = state["messages"][-1]
    
    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        print(f"\n  [실행] {tool_name}({tool_args})")
        
        for t in tools:
            if t.name == tool_name:
                result = t.invoke(tool_args)
                print(f"  [결과] {result}")
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


# ===== 그래프 =====
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

# 핵심: 도구 실행 직전에 중단
checkpointer = MemorySaver()
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["execute_tools"]  # 도구 실행 전 멈춤
)


# ===== 실행 헬퍼 =====

def is_dangerous_call(state):
    """이번에 호출될 도구가 위험한지 판단"""
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls"):
        return False, []
    
    dangerous_calls = []
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in DANGEROUS_TOOLS:
            dangerous_calls.append(tool_call)
    
    return len(dangerous_calls) > 0, dangerous_calls


def run_with_approval(question: str, thread_id: str = "session-1"):
    """HITL 에이전트 실행"""
    print("=" * 70)
    print(f"질문: {question}")
    print("=" * 70)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # 첫 실행
    initial = {"messages": [HumanMessage(content=question)]}
    
    # invoke가 중단점 만나면 멈춤
    result = app.invoke(initial, config)
    
    # 반복: 중단되면 검토 → 승인/거절 → 재개
    while True:
        # 현재 state 확인
        snapshot = app.get_state(config)
        
        # 다음 노드 없으면 끝
        if not snapshot.next:
            break
        
        # execute_tools 직전이면 검토
        if "execute_tools" in snapshot.next:
            is_dangerous, dangerous_calls = is_dangerous_call(snapshot.values)
            
            if is_dangerous:
                # 위험 도구 호출 → 사람 승인 필요
                print(f"\n⚠️  위험한 작업이 요청되었습니다:")
                for call in dangerous_calls:
                    print(f"   - {call['name']}({call['args']})")
                
                response = input("\n승인하시겠습니까? (y/n): ").strip().lower()
                
                if response != "y":
                    print("❌ 거절됨. 에이전트 종료.")
                    return
                
                print("✅ 승인됨. 실행합니다.")
            else:
                # 안전한 도구는 자동 진행
                print("\n(안전한 도구. 자동 진행)")
            
            # 재개
            result = app.invoke(None, config)
        else:
            break
    
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
    # 시나리오 1: 안전한 도구만 (자동 진행)
    print("\n" + "★" * 70)
    print("시나리오 1: 안전한 작업 (검색만)")
    print("★" * 70)
    run_with_approval(
        "철수 정보 찾아줘",
        thread_id="session-safe"
    )
    
    # 시나리오 2: 위험한 도구 (승인 필요)
    print("\n\n" + "★" * 70)
    print("시나리오 2: 위험한 작업 (점수 변경)")
    print("★" * 70)
    run_with_approval(
        "user_1의 점수를 50으로 변경해줘",
        thread_id="session-update"
    )
    
    # 시나리오 3: 위험한 도구 (삭제)
    print("\n\n" + "★" * 70)
    print("시나리오 3: 매우 위험한 작업 (삭제)")
    print("★" * 70)
    run_with_approval(
        "user_3을 데이터베이스에서 영구 삭제해줘. 확인했으니 진행해.",
        thread_id="session-delete-2"
    )