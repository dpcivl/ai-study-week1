import os
import random
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# 도구 정의
weather_tool = {
    "name": "get_weather",
    "description": "특정 도시의 현재 날씨를 조회합니다. 사용자가 날씨를 물어볼 때 사용하세요.",
    "input_schema": {
        "type": "object", 
        "properties": {
            "city": {
                "type": "string",
                "description": "날씨를 조회할 도시 이름 (한글 또는 영문)"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "온도 단위",
                "default": "celsius"
            }
        },
        "required": ["city"]
    }
}

# 실제 도구 함수 (가짜 데이터)
def get_weather(city, unit="celsius"):
    """실제로는 외부 API 호출해야 함. 학습용 더미 데이터."""
    weather_db = {
        "부산": {"temp_c": 22, "condition": "맑음", "humidity": 65},
        "서울": {"temp_c": 18, "condition": "흐림", "humidity": 70},
        "Seoul": {"temp_c": 18, "condition": "흐림", "humidity": 70},
        "Busan": {"temp_c": 22, "condition": "맑음", "humidity": 65},
        "Tokyo": {"temp_c": 20, "condition": "비", "humidity": 85}, 
    }

    if city not in weather_db:
        return {"error": f"{city}의 날씨 정보를 찾을 수 없습니다"}
    
    data = weather_db[city]
    temp = data["temp_c"]
    if unit == "fahrenheit":
        temp = temp * 9/5 + 32

    return {
        "city": city,
        "temparature": temp,
        "unit": "unit",
        "condition": data["condition"],
        "humidity": data["humidity"]
    }

# 도구 실행 헬퍼 함수
def run_tool(tool_name, tool_input):
    """도구 이름에 따라 적절한 함수 호출"""
    if tool_name == "get_weather":
        return get_weather(**tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}
    
# 에이전트 루프 (Tool Use 표준 패턴)
def run_agent(user_message, tools, tool_runner):
    """
    LLM이 도구를 다 쓸 때까지 반복 호출
    Tool Use의  일반적 패턴
    """
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        # LLM의 응답 추가
        messages.append({"role": "assistant", "content": response.content})

        # 도구 호출이 없으면 종료
        if response.stop_reason != "tool_use":
            # 텍스트 응답 추출해서 반환
            for block in response.content:
                if block.type == "text":
                    return block.text
                return ""
            
        # 도구 호출들 처리
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\n[도구 호출] {block.name}({block.input})")
                result = tool_runner(block.name, block.input)
                print(f"[결과] {result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

        # 모든 도구 결과를 한 번에 user 메시지로 추가
        messages.append({"role": "user", "content": tool_results})

# 실행
print("=" * 60)
print("질문: 부산이랑 서울 날씨 비교해줘")
print("=" * 60)

answer = run_agent(
    user_message="부산이랑 서울 날씨 비교해줘", 
    tools=[weather_tool],
    tool_runner=run_tool
)

print(f"\n[최종 답변]\n{answer}")