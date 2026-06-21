import os
import json
from typing import TypedDict, Annotated
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()


# ===== State =====
class LearningAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_name: str
    learning_progress: dict     # 학습 진행 상황
    tool_call_count: int
    notes_added: list           # 추가된 메모


# ===== 도구들 =====

# 가짜 학습 진행 데이터 (실제론 DB나 파일)
LEARNING_DATA = {
    "Week 1": ["Day 1: 환경 셋업", "Day 2: API 첫 호출", "Day 3: 멀티턴", 
               "Day 4: 시스템 프롬프트", "Day 5: 스트리밍", "Day 6: Tool Use", "Day 7: Vision"],
    "Week 2": ["Day 1: Prompt Caching", "Day 2: 에러 핸들링"],
    "Week 3": ["Day 1: RAG 기초", "Day 2: 진짜 RAG 시스템"],
    "Week 4": ["Day 1: LangGraph 시작", "Day 2: 복잡한 에이전트"] 
}

@tool
def get_learning_progress(week: str = "") -> str:
    """학습 진행 상황을 조회합니다. week는 'Week 1', 'Week 2' 등으로 지정. 비우면 전체."""
    if week:
        if week in LEARNING_DATA:
            items = LEARNING_DATA[week]
            return f"{week} 진행:\n" + "\n".join(f"  - {item}" for item in items)
        else:
            return f"{week} 데이터 없음"
        
    result = "전체 학습 진행:\n"
    for w, items in LEARNING_DATA.items():
        result += f"\n{w} ({len(items)}개 완료):\n"
        for item in items:
            result += f"  - {item}\n"
    return result

@tool
def add_learning_note(topic: str, note: str) -> str:
    """학습 메모를 추가합니다. topic은 주제, note는 메모 내용."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"메모 추가 완료 ({timestamp})\n주제: {topic}\n내용: {note}"

@tool
def search_concept(concept: str) -> str:
    """학습 개념을 검색합니다. 예: 'LangGraph State', 'Tool Use'."""
    # 가짜 데이터베이스 (실제론 RAG 시스템 호출)
    knowledge = {
        "LangGraph State": "노드들이 공유하는 데이터. TypedDict로 정의. reducer로 업데이트 방식 제어.",
        "Tool Use": "LLM이 외부 함수를 호출하는 메커니즘. Anthropic API의 tools 파라미터로 정의.",
        "RAG": "Retrieval-Augmented Generation. 검색 + LLM 생성 결합.",
        "임베딩": "텍스트를 의미 보존하는 고차원 벡터로 변환.",
        "에이전트": "LLM이 도구 사용하며 자율적으로 목표 달성하는 시스템.",
    }

    if concept in knowledge:
        return f"[{concept}]\n{knowledge[concept]}"
    
    # 부분 매칭
    matches = [k for k in knowledge.keys() if concept.lower() in k.lower()]
    if matches:
        return f"비슷한 개념 있음: {', '.join(matches)}"
    
    return f"'{concept}' 정보 없음. 다른 키워드로 시도해보세요. "

@tool
def calculate_streak(days_active: int) -> str:
    """학습 스트릭(연속 일수)에 대한 평가를 반환합니다."""
    if days_active >= 30:
        return f"🔥 {days_active}일! 대단해요! 한 달 넘게 꾸준히 학습 중이네요."
    elif days_active >= 7:
        return f"✨ {days_active}일! 일주일 넘게 꾸준해요. 계속 갑시다."
    elif days_active >= 3:
        return f"👍 {days_active}일! 좋은 시작이에요."
    else:
        return f"{days_active}일째 학습 중. 꾸준함이 중요해요!"
    # 이 부분은 복붙했음.. 이모지 붙이기 귀찮아서

tools = [get_learning_progress, add_learning_note, search_concept, calculate_streak]


# ===== LLM =====
llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0
).bind_tools(tools)


# ===== 노드 =====
def initialize(state: LearningAgentState):
    print(f"\n[initialize] 학습 도우미 시작")

    # 가짜 초기 진행 상황
    initial_progress = {
        "total_days": 5,
        "current_week": "Week 4",
        "current_day": "Day 2"
    }

    return {
        "learning_progress": initial_progress,
        "tool_call_count": 0,
        "notes_added": []
    }

def call_llm(state: LearningAgentState):
    progress = state.get("learning_progress", {})

    system_content = f"""당신은 1인 개발자의 친근한 학습 도우미입니다. 

사용자 정보:
- 이름: {state.get('user_name', '학습자')}
- 학습 중인 주차: {progress.get('current_week', '알 수 없음')}
- 학습 중인 일: {progress.get('current_day', '알 수 없음')}
- 학습 일수: {progress.get('total_days', 0)}일

사용 가능한 도구:
- get_learning_progress: 학습 진행 조회
- add_learning_note: 학습 메모 추가
- search_concept: 개념 검색
- calculate_streak: 학습 스트릭 평가

규칙:
- 한국어로 친근하게
- 사용자 이름 자연스럽게 호명
- 필요하면 도구 적극 사용
- 학습 동기 부여하는 톤"""
    
    messages_with_system = [SystemMessage(content=system_content)] + state["messages"]
    response = llm.invoke(messages_with_system)

    return {"messages": [response]}


def execute_tools(state: LearningAgentState):
    last_message = state["messages"][-1]

    tool_results = []
    notes_added = list(state.get("notes_added", []))

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        print(f"  도구 호출: {tool_name}({tool_args})")

        for t in tools:
            if t.name == tool_name:
                result = t.invoke(tool_args)
                print(f"  결과 (첫 100자): {str(result)[:100]}...")

                # add_learning_note가 호출되면 State에도 기록
                if tool_name == "add_learning_note":
                    notes_added.append({
                        "topic": tool_args.get("topic", ""),
                        "note": tool_args.get("note", "")
                    })

                tool_results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
                break


    return {
        "messages": tool_results,
        "tool_call_count": state.get("tool_call_count", 0) + len(tool_results),
        "notes_added": notes_added
    }

def should_continue(state: LearningAgentState):
    last_message = state["messages"][-1]

    if state.get("tool_call_count", 0) >= 10:
        return "end"
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return "end"


# ===== 그래프 =====
workflow = StateGraph(LearningAgentState)
workflow.add_node("initialize", initialize)
workflow.add_node("call_llm", call_llm)
workflow.add_node("execute_tools", execute_tools)

workflow.set_entry_point("initialize")
workflow.add_edge("initialize", "call_llm")
workflow.add_conditional_edges(
    "call_llm",
    should_continue,
    {"execute_tools": "execute_tools", "end": END}
)
workflow.add_edge("execute_tools", "call_llm")

app = workflow.compile()



# ===== 실행 =====
def chat(question: str, user_name: str = "학습자"):
    print("=" * 70)
    print(f"질문: {question}")
    print("=" * 70)

    initial_state = {
        "messages": [HumanMessage(content=question)],
        "user_name": user_name,
        "learning_progress": {},
        "tool_call_count": 0,
        "notes_added": []
    }

    final_state = app.invoke(initial_state)

    final_message = final_state["messages"][-1]
    print(f"\n[답변]")
    if isinstance(final_message.content, str):
        print(final_message.content)
    else:
        for block in final_message.content:
            if isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text", ""))
    
    if final_state.get("notes_added"):
        print(f"\n[추가된 메모: {len(final_state['notes_added'])}개]")
        for note in final_state["notes_added"]:
            print(f"  - {note['topic']}: {note['note'][:50]}...")


if __name__ == "__main__":
    USER = "본인이름"
    
    # 시나리오 1: 진행 상황 조회
    chat("내 학습 진행 상황 보여줘", user_name=USER)
    print("\n")
    
    # 시나리오 2: 개념 검색
    chat("LangGraph State 개념 다시 설명해줘", user_name=USER)
    print("\n")
    
    # 시나리오 3: 멀티 도구 호출
    chat("Week 3에 뭐 배웠는지 보여주고, 'RAG 청크 분할'이라는 메모 추가해줘. "
         "그리고 내가 5일째 학습 중인데 어때?", user_name=USER)