from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# 간단한 카운터 State
class CounterState(TypedDict):
    count: Annotated[int, add]
    history: Annotated[list, add]

def step1(state: CounterState):
    print(f"\n[Step 1] 현재 count: {state['count']}")
    return {
        "count": 10,
        "history": ["step1 done"]
    }

def step2(state: CounterState):
    print(f"\n[Step 2] 현재 count: {state['count']}")
    return {
        "count": 20,
        "history": ["step2 done"]
    }

def step3(state: CounterState):
    print(f"\n[Step 3] 현재 count: {state['count']}")
    return {
        "count": 30, 
        "history": ["step3 done"]
    }


# 그래프 빌드
workflow = StateGraph(CounterState)
workflow.add_node("step1", step1)
workflow.add_node("step2", step2)
workflow.add_node("step3", step3)

workflow.set_entry_point("step1")
workflow.add_edge("step1", "step2")
workflow.add_edge("step2", "step3")
workflow.add_edge("step3", END)

# 핵심: 체크포인트 추가
checkpointer = MemorySaver()    # 메모리에 저장 (실전은 SqliteSaver, PostgreSaver 등)

# step2 전에 멈추도록 설정
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["step2"]      # 핵심: step2 직전에 멈춤
)

# ===== 실행 =====
# thread_id: 대화/세션 식별자 (멀티 사용자/세션 구분)
config = {"configurable": {"thread_id": "demo-1"}}

print("=" * 60)
print("실행 1: step1만 실행 후 중단")
print("=" * 60)

initial = {"count": 0, "history": []}

# invoke가 step2 전에서 멈춤
result = app.invoke(initial, config)
print(f"\n중단된 시점의 state: {result}")

# 현재 어디서 멈춰 있나? 
state = app.get_state(config)
print(f"\n다음 실행 예정 노드: {state.next}")
print(f"State: {state.values}")

print("\n" + "=" * 60)
print("실행 2: 사람 승인 받았다 치고 재개")
print("=" * 60)

# 같은 thread_id로 재개. None 입력하면 중단 지점부터 계속
result = app.invoke(None, config)
print(f"\n최종 state: {result}")