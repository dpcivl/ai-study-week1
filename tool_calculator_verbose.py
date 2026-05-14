import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client= Anthropic()

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
                "enum": ["add", "subtract", "multiply", "divide"],
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
    

def print_messages(messages, step):
    """messages 배열 상태를 보기 좋게 출력"""
    print(f"\n{'='*60}")
    print(f"[Step {step}] messages 상태")
    print(f"{'='*60}")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]
        print(f"\n [{i}] role: {role}")
        if isinstance(content, str):
            print(f"  content: {content[:80]}...")
        else:
            for block in content:
                if hasattr(block, 'type'):
                    block_type = block.type
                else:
                    block_type = block.get('type', 'unknown')
                print(f"  block type: {block_type}")

# 실행
user_question = "847 곱하기 2391은?"
messages = [{"role": "user", "content": user_question}]

print_messages(messages, "1: 사용자 질문만")

# 1차 호출
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    tools=[calculator_tool],
    messages=messages
)

# assistant 응답 추가
messages.append({"role": "assistant", "content": response.content})
print_messages(messages, "2: LLM이 도구 호출 결정")

# 도구 실행
tool_use_block = next(b for b in response.content if b.type == "tool_use")
result = calculator(**tool_use_block.input)

# 도구 결과 추가
messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": tool_use_block.id,
        "content": str(result)
    }]
})
print_messages(messages, "3: 도구 결과 추가")

# 2차 호출
final_response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    tools=[calculator_tool],
    messages=messages
)

messages.append({"role": "assistant", "content": final_response.content})
print_messages(messages, "4: 최종 답변 추가")

print("\n" + "="*60)
print("최종 답변:")
print("="*60)
for block in final_response.content:
    if block.type == "text":
        print(block.text)