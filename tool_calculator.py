import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# ===== 1단계: 도구 정의 =====
# 도구의 명세를 JSON Schema 형태로 정의
calculator_tool = {
    "name": "calculator",
    "description": "정확한 사칙연산을 수행합니다. 큰 수의 곱셈이나 정확도가 중요한 계산에 사용하세요.",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "substract", "multiply", "divide"],
                "description": "수행할 연산"
            },
            "a": {
                "type": "number",
                "description": "첫 번째 숫자"
            },
            "b": {
                "type": "number",
                "description": "두 번째 숫자"
            }
        },
        "required": ["operation", "a", "b"]
    }
}

# ===== 2단계: 실제 도구 함수 (Python 코드) =====
def calculator(operation, a, b):
    """실제로 계산을 수행하는 함수"""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            return "Error: division by zero"
        return a / b
    else:
        return f"Error: unknown operation {operation}"
    
# ===== 3단계: 사용자 질문 =====
user_question = "847 곱하기 2391은?"

print(f"사용자 질문: {user_question}")
print("=" * 60)

# 첫 번째 메시지
messages = [
    {"role": "user", "content": user_question}
]

# ===== 4단계: LLM 호출 (도구 명세 포함) =====
print("\n[1차 LLM 호출] tools 파라미터 추가")
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    tools=[calculator_tool],
    messages=messages
)

print(f"  stop_reason: {response.stop_reason}")
# 'tool_use'면 도구를 쓰기로 결정한 것
# 'end_turn'이면 그냥 답변한 것

# ===== 5단계: 응답 분석 =====
print("\n[응답 분석]")
for block in response.content:
    print(f" 블록 타입: {block.type}")
    if block.type == "text":
        print(f"  텍스트: {block.text}")
    elif block.type == "tool_use":
        print(f"  도구 이름: {block.name}")
        print(f"  도구 ID: {block.id}")
        print(f"  도구 인자: {block.input}")

# ===== 6단계: 도구 사용 결정이면, 실행 =====
if response.stop_reason == "tool_use":
    # tool_use 블록 찾기
    tool_use_block = next(
        block for block in response.content
        if block.type == "tool_use"
    )

    tool_name = tool_use_block.name
    tool_input = tool_use_block.input
    tool_use_id = tool_use_block.id

    print(f"\n[도구 실행] {tool_name}({tool_input})")

    # 실제 함수 호출
    if tool_name == "calculator":
        result = calculator(**tool_input)
        print(f"  실행 결과: {result}")

    # ===== 7단계: 결과를 LLM에 다시 전달 =====
    # messages에 추가할 것들:
    # 1. LLM이 한 응답 (tool_use 블록 포함)
    # 2. tool_result 메시지 (사용자 역할로)

    messages.append({
        "role": "assistant",
        "content": response.content  # tool_use 블록을 그대로 포함
    })

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": str(result)
            }
        ]
    })

    print("\n[2차 LLM 호출] 도구 결과 전달")

    # 두 번째 LLM 호출
    final_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens = 1024,
        tools=[calculator_tool],
        messages=messages
    )

    print(f"\n[최종 답변]")
    for block in final_response.content:
        if block.type == "text":
            print(block.text)