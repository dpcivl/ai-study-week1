"""
도구 선택 정확도 Eval
에이전트가 질문에 맞는 도구를 선택하는지 측정
"""
import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()


# ===== 테스트할 도구들 =====
tools = [
    {
        "name": "calculator",
        "description": "수학 계산을 수행합니다. 사칙연산, 큰 수 곱셈 등.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "계산식"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_weather",
        "description": "특정 도시의 현재 날씨를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "도시 이름"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "search_web",
        "description": "웹에서 정보를 검색합니다. 최신 뉴스, 일반 지식 등.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어"}
            },
            "required": ["query"]
        }
    }
]

# ===== 테스트 케이스 (질문 + 기대 도구) =====
test_cases = [
    {"question": "847 곱하기 2391은?", "expected_tool": "calculator"},
    {"question": "부산 날씨 어때?", "expected_tool": "get_weather"},
    {"question": "오늘 주요 뉴스 알려줘", "expected_tool": "search_web"},
    {"question": "100을 7로 나누면?", "expected_tool": "calculator"},
    {"question": "서울 지금 추워?", "expected_tool": "get_weather"},
    {"question": "파이썬 최신 버전이 뭐야?", "expected_tool": "search_web"},
    {"question": "1234 더하기 5678은?", "expected_tool": "calculator"},
    {"question": "도쿄 기온 알려줘", "expected_tool": "get_weather"},
    {"question": "비트코인 가격 검색해줘", "expected_tool": "search_web"},
    {"question": "15의 제곱은?", "expected_tool": "calculator"},
]


def get_selected_tool(question):
    """LLM이 어떤 도구를 선택하는지 확인"""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        tools=tools,
        tool_choice={"type": "any"},    # 무조건 도구 하나 선택하게
        messages=[{"role": "user", "content": question}]
    )

    # 선택된 도구 찾기
    for block in response.content:
        if block.type == "tool_use":
            return block.name
        return None
    

def run_eval():
    """전체 eval 실행"""
    print("=" * 70)
    print("도구 선택 정확도 Eval")
    print("=" * 70)

    results = []
    correct = 0

    for i, case in enumerate(test_cases, 1):
        question = case["question"]
        expected = case["expected_tool"]

        # LLM이 선택한 도구
        selected = get_selected_tool(question)

        is_correct = (selected == expected)
        if is_correct:
            correct += 1

        results.append({
            "question": question,
            "expected": expected,
            "selected": selected,
            "correct": is_correct
        })

        # 출력
        status = "v" if is_correct else "x"
        print(f"\n{i}. {status} {question}")
        print(f"  기대: {expected}, 선택: {selected}")

    # ===== 통계 =====
    total = len(test_cases)
    accuracy = correct / total * 100

    print("\n" + "=" * 70)
    print("결과")
    print("=" * 70)
    print(f"정확도: {correct}/{total} = {accuracy:.1f}%")

    # 틀린 케이스 분석
    wrong_cases = [r for r in results if not r["correct"]]
    if wrong_cases:
        print(f"\n틀린 케이스 ({len(wrong_cases)}개):")
        for w in wrong_cases:
            print(f"  - '{w['question']}'")
            print(f"    기대: {w['expected']}, 선택:{w['selected']}")
    else:
        print("\n모든 케이스 정확!")

    # 결과 저장
    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: eval_results.json")

    return accuracy


if __name__=="__main__":
    run_eval()