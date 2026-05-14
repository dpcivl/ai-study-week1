import os
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# ===== 도구 3개 정의 =====

calculator_tool = {
    "name": "calculator",
    "description": "사칙연산 수행",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["operation", "a", "b"]
    }
}

get_time_tool = {
    "name": "get_current_time",
    "description": "현재 시간을 조회합니다",
    "input_schema": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string", 
                "description": "타임존 (예: 'Asia/Seoul', 'UTC')",
                "default": "Asia/Seoul"
            }
        }
    }
}

weather_tool = {
    "name": "get_weather",
    "description": "도시의 현재 날씨 조회",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"}
        },
        "required": ["city"]
    }
}

# ===== 실제 함수들 =====
def calculator(operation, a, b):
    ops = {"add": a+b, "subtract": a-b, "multiply": a*b, "divide": a/b if b else "div by zero"}
    return ops.get(operation, "unknown op")

def get_current_time(timezone="Asia/Seoul"):
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f" ({timezone})"

def get_weather(city):
    weather_db = {
        "부산": "맑음, 22도",
        "서울": "흐림, 18도", 
        "도쿄": "비, 20도"
    }
    return weather_db.get(city, f"{city} 날씨 정보 없음")

# 도구 라우터
def run_tool(tool_name, tool_input):
    if tool_name == "calculator":
        return calculator(**tool_input)
    elif tool_name == "get_current_time":
        return get_current_time(**tool_input)
    elif tool_name == "get_weather":
        return get_weather(**tool_input)
    return "Unknown tool"

# 에이전트 루프
def run_agent(user_message, tools, tool_runner, verbose=True):
    messages = [{"role": "user", "content": user_message}]

    iteration = 0
    while True:
        iteration += 1
        if verbose:
            print(f"\n--- Iteration {iteration} ---")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""
        
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if verbose:
                    print(f"  도구 호출: {block.name}({block.input})")
                result = tool_runner(block.name, block.input)
                if verbose:
                    print(f"  결과: {result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

        messages.append({"role": "user", "content": tool_results})

        # 무한 루프 방지
        if iteration >= 10:
            print("최대 반복 횟수 도달")
            break

# ===== 테스트 =====

all_tools = [calculator_tool, get_time_tool, weather_tool]

# 테스트 1: 단순한 도구 하나
print("=" * 60)
print("테스트 1: 단순 질문")
print("=" * 60)
print("질문: 지금 몇 시야?")
answer = run_agent("지금 몇 시야", all_tools, run_tool)
print(f"\n[답변]\n{answer}")

# 테스트 2: 여러 도구 조합
print("\n\n" + "=" * 60)
print("테스트 2: 복합 질문")
print("=" * 60)
print("질문: 지금 부산 날씨 알려주고, 22 곱하기 31도 계산해줘")
answer = run_agent(
    "지금 부산 날씨 알려주고, 22 곱하기 31도 계산해줘",
    all_tools,
    run_tool
)
print(f"\n[답변]\n{answer}")

# 테스트 3: 도구가 필요 없는 질문
print("\n\n" + "=" * 60)
print("테스트 3: 도구 불필요 질문")
print("=" * 60)
print("질문: 파이썬에서 리스트 컴프리헨션이 뭐야?")
answer = run_agent("파이썬에서 리스트 컴프리헨션이 뭐야?", all_tools, run_tool)
print(f"\n[답변]\n{answer}")