import os
from pathlib import Path
from typing import TypedDict, Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()


# 작업 디렉토리 (안전을 위해 특정 폴더로 제한)
WORKSPACE = Path("./test_workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)


def is_safe_path(filepath: str) -> bool:
    """경로가 WORKSPACE 안에 있는지 확인 (보안)"""
    try:
        path = Path(filepath).resolve()
        return WORKSPACE in path.parents or path == WORKSPACE
    except:
        return False


# ===== 도구들 =====

@tool
def list_files() -> str:
    """작업 디렉토리의 파일 목록을 반환합니다 (안전)."""
    files = list(WORKSPACE.rglob("*"))
    if not files:
        return f"{WORKSPACE}: 파일 없음"
    
    result = f"{WORKSPACE}:\n"
    for f in sorted(files):
        if f.is_file():
            size = f.stat().st_size
            result += f"  {f.relative_to(WORKSPACE)} ({size} bytes)\n"
    return result


@tool
def read_file(filename: str) -> str:
    """파일 내용을 읽습니다 (안전)."""
    filepath = WORKSPACE / filename
    
    if not is_safe_path(str(filepath)):
        return "오류: WORKSPACE 외부 경로"
    
    if not filepath.exists():
        return f"파일 없음: {filename}"
    
    try:
        content = filepath.read_text(encoding="utf-8")
        return f"파일: {filename}\n내용:\n{content}"
    except Exception as e:
        return f"읽기 오류: {e}"


@tool
def write_file(filename: str, content: str) -> str:
    """파일에 내용을 씁니다 (⚠️ 위험 - 덮어쓰기)."""
    filepath = WORKSPACE / filename
    
    if not is_safe_path(str(filepath)):
        return "오류: WORKSPACE 외부 경로"
    
    try:
        # 기존 파일이 있으면 백업 정보
        existed = filepath.exists()
        old_size = filepath.stat().st_size if existed else 0
        
        filepath.write_text(content, encoding="utf-8")
        
        new_size = filepath.stat().st_size
        if existed:
            return f"파일 덮어쓰기 완료: {filename} ({old_size} → {new_size} bytes)"
        else:
            return f"새 파일 생성 완료: {filename} ({new_size} bytes)"
    except Exception as e:
        return f"쓰기 오류: {e}"


@tool
def delete_file(filename: str) -> str:
    """파일을 삭제합니다 (⚠️ 매우 위험 - 영구 삭제)."""
    filepath = WORKSPACE / filename
    
    if not is_safe_path(str(filepath)):
        return "오류: WORKSPACE 외부 경로"
    
    if not filepath.exists():
        return f"파일 없음: {filename}"
    
    try:
        size = filepath.stat().st_size
        filepath.unlink()
        return f"파일 삭제 완료: {filename} ({size} bytes 사라짐)"
    except Exception as e:
        return f"삭제 오류: {e}"


# 위험한 도구
DANGEROUS_TOOLS = {"write_file", "delete_file"}

tools = [list_files, read_file, write_file, delete_file]


# ===== State =====
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ===== LLM =====
llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0
).bind_tools(tools)


def call_llm(state: State):
    system_content = f"""당신은 파일 시스템 도우미 에이전트입니다.

작업 디렉토리: {WORKSPACE}

도구:
- list_files: 파일 목록 조회 (안전)
- read_file: 파일 읽기 (안전)
- write_file: 파일 쓰기/덮어쓰기 (⚠️ 위험)
- delete_file: 파일 삭제 (⚠️ 매우 위험)

규칙:
- 파일명 정확히 알고 있을 때만 수정 시도
- 한국어로 자연스럽게"""

    response = llm.invoke([SystemMessage(content=system_content)] + state["messages"])
    return {"messages": [response]}


def execute_tools(state: State):
    last_message = state["messages"][-1]
    tool_results = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        print(f"\n  [실행] {tool_name}({tool_args})")
        
        for t in tools:
            if t.name == tool_name:
                result = t.invoke(tool_args)
                print(f"  [결과] {result[:200]}")
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

checkpointer = MemorySaver()
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["execute_tools"]
)


# ===== HITL 실행 =====

def show_pending_action(state):
    """대기 중인 도구 호출 보여주기"""
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls"):
        return False, []
    
    has_dangerous = False
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in DANGEROUS_TOOLS:
            has_dangerous = True
            print(f"\n⚠️  위험한 작업 요청:")
            print(f"   도구: {tool_call['name']}")
            for key, value in tool_call["args"].items():
                # content가 너무 길면 자르기
                if isinstance(value, str) and len(value) > 200:
                    print(f"   {key}: {value[:200]}... (총 {len(value)}자)")
                else:
                    print(f"   {key}: {value}")
    
    return has_dangerous, last_message.tool_calls


def interactive_session(user_input: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"\n사용자: {user_input}")
    print("-" * 70)
    
    current_state = app.get_state(config)
    
    if current_state.next and "execute_tools" in current_state.next:
        # 중단점에서 재개 (드문 케이스)
        app.invoke(None, config)
    else:
        # 새 메시지로 시작/이어가기
        # add_messages가 자동 누적해줌
        app.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config
        )
    
    # 중단점 처리 루프
    while True:
        snapshot = app.get_state(config)
        
        if not snapshot.next:
            break
        
        if "execute_tools" in snapshot.next:
            is_dangerous, _ = show_pending_action(snapshot.values)
            
            if is_dangerous:
                response = input("\n승인하시겠습니까? (y/n/edit): ").strip().lower()
                
                if response == "y":
                    print("✅ 승인. 실행합니다.")
                    app.invoke(None, config)
                elif response == "edit":
                    print("(편집 기능은 다음 단계에서)")
                    # 도구 호출 자체 수정 가능. 일단 거절 처리.
                    print("❌ 거절. 다른 방법 요청 가능.")
                    return
                else:
                    print("❌ 거절. 종료.")
                    return
            else:
                # 안전한 도구 자동 진행
                app.invoke(None, config)
        else:
            break
    
    # 최종 답변
    final_state = app.get_state(config).values
    if final_state.get("messages"):
        final_message = final_state["messages"][-1]
        print(f"\nAI: ", end="")
        if isinstance(final_message.content, str):
            print(final_message.content)
        else:
            for block in final_message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    print(block.get("text", ""))


if __name__ == "__main__":
    THREAD = "file-session-1"
    
    print(f"\n파일 시스템 에이전트 시작")
    print(f"작업 디렉토리: {WORKSPACE}")
    print("=" * 70)
    
    # 시나리오: 파일 만들고 → 확인 → 수정 → 삭제
    interactive_session("현재 파일 목록 보여줘", THREAD)
    interactive_session("hello.txt 파일 만들어줘. 내용은 '안녕하세요'로.", THREAD)
    interactive_session("hello.txt 읽어줘", THREAD)
    interactive_session("hello.txt 내용을 '반갑습니다'로 바꿔줘", THREAD)
    interactive_session("hello.txt 삭제해줘", THREAD)