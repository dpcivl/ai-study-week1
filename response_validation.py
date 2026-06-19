import os
import json
import time
import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def extract_json(text):
    """텍스트에서 JSON 부분만 추출"""
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != 0:
        return text[start:end]
    return None    # 이거 자주 쓰이니까 눈에 익히자. 

def validate_analysis_response(text):
    """응답이 우리가 원하는 형식인지 검증"""
    try:
        # JSON 추출
        json_str = extract_json(text)
        if not json_str:
            return False, "JSON 형식 없음"
        
        # JSON 파싱
        data = json.loads(json_str)

        # 필수 필드 확인
        required_fields = ["summary", "language", "issues", "scores"]
        for field in required_fields:
            if field not in data:
                return False, f"필수 필드 누락: {field}"
            
        # 타입 확인
        if not isinstance(data["issues"], list):
            return False, "'issues'는 리스트여야 함"
        
        if not isinstance(data["scores"], dict):
            return False, "'scores'는 딕셔너리여야 함"
        
        # 점수 범위 확인
        for key, value in data["scores"].items():
            if not isinstance(value, (int, float)):
                return False, f"점수 '{key}'가 숫자가 아님"
            if value < 0 or value > 10:
                return False, f"점수 '{key}'가 0-10 범위 벗어남"
            
        return True, data
    
    except json.JSONDecodeError as e:
        return False, f"JSON 파싱 실패: {e}"
    except Exception as e:
        return False, f"검증 중 에러: {e}"
    
def analyze_code_with_retry(code, max_retries=3):
    """
    코드 분석을 시도하되, 응답이 형식 안 맞으면 재시도
    재시도 시 LLM에게 무엇이 잘못됐는지 알려줌
    """

    system = """당신은 코드 분석 도구입니다. 
응답은 반드시 다음 JSON 형식으로만:
{
    "summary": "한 줄 요약",
    "language": "프로그래밍 언어",
    "issues": [
        {"severity": "high|medium|low", "description": "문제 설명"}
        ],
    "scores": {
        "readability": 0-10 점수,
        "efficiency": 0-10 점수,
        "safety": 0-10 점수
        }
}

다른 텍스트 포함 금지. 마크다운 코드블록 금지.
"""

    messages = [
        {"role": "user", "content": f"이 코드 분석해줘:\n```\n{code}\n```"}
    ]

    for attempt in range(max_retries):
        print(f"\n[시도 {attempt+1}/{max_retries}]")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=messages
        )

        text = response.content[0].text
        print(f"응답 길이: {len(text)}자")

        # 검증
        is_valid, result = validate_analysis_response(text)

        if is_valid:
            print(f"검증 성공!")
            return result
        
        print(f"검증 실패: {result}")

        # 마지막 시도였으면 포기
        if attempt == max_retries - 1:
            print(f"모든 재시도 실패")
            return None
        
        # LLM에게 무엇이 잘못됐는지 알려주고 재시도
        messages.append({"role": "assistant", "content": text})
        messages.append({
            "role": "user", 
            "content": f"형식이 잘못됐습니다. 문제: {result}. JSON 형식을 정확히 지켜서 다시 응답해주세요."
        })

# ===== 테스트 =====
test_code = """
def divide(a, b):
    return a / b
"""

print("=" * 60)
print("응답 검증 + 재시도 테스트")
print("=" * 60)
print(f"분석할 코드:\n{test_code}")

result = analyze_code_with_retry(test_code)

if result:
    print("\n" + "=" * 60)
    print("최종 결과:")
    print("=" * 60)
    print(f"요약: {result['summary']}")
    print(f"언어: {result['language']}")
    print(f"문제 수: {len(result['issues'])}")
    print(f"점수: {result['scores']}")
else:
    print("\n분석 실패")