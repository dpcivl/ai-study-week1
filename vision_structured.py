import os
import base64
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")
    
def get_media_type(image_path):
    ext = image_path.lower().split('.')[-1]
    types = {"jpg": "images/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
    return types.get(ext, "image/jpeg")

# 시스템 프롬프트로 출력 형식 강제
system = """당신은 이미지 분석 도구입니다. 
이미지를 분석한 결과를 **반드시 유효한 JSON 형식으로만** 응답하세요. 

응답 형식:
{
    "main_subject": "이미지의 주요 피사체",
    "objects": ["감지된 물체들"],
    "colors": ["주요 색상들"],
    "mood": "이미지의 분위기",
    "estimated_location": "촬영 장소 추정 (예: 실내/실외, 도시/자연)",
    "text_in_image": "이미지 안의 텍스트 (없으면 null)",
    "quality_score": 1-10 점수
    "tags": ["검색 가능한 태그들"]
}

JSON 외 다른 텍스트 포함 금지. 마크다운 코드 블록도 사용 금지"""

image_path = "images/test2.png"

print(f"구조화된 분석: {image_path}")
print("=" * 60)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system=system,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": get_media_type(image_path),
                        "data": encode_image(image_path)
                    }
                },
                {
                    "type": "text",
                    "text": "이 이미지를 분석해서 JSON으로 응답해줘."
                }
            ]
        }
    ]
)

raw_response = response.content[0].text
print("Raw 응답:")
print(raw_response)
print()

# JSON 파싱
try:
    # 안전한 파싱: 첫 { 부터 마지막 } 까지 추출
    start = raw_response.find('{')
    end = raw_response.rfind('}') + 1
    clean_json = raw_response[start:end]

    result = json.loads(clean_json)

    print("=" * 60)
    print("파싱 성공! 구조화된 데이터 활용")
    print("=" * 60)

    print(f"\n주요 피사체: {result['main_subject']}")
    print(f"감지된 물체: {', '.join(result['objects'])}")
    print(f"주요 색상: {', '.join(result['colors'])}")
    print(f"분위기: {result['mood']}")
    print(f"위치: {result['estimated_location']}")
    print(f"품질 점수: {result['quality_score']}/10")
    print(f"태그: {', '.join(result['tags'])}")

    if result.get('text_in_image'):
        print(f"이미지 내 텍스트: {result['text_in_image']}")

    # 이 시점부터 result는 일반 Python dict
    # 데이터베이스 저장, API 응답, 다른 시스템 전달 모두 가능

except json.JSONDecodeError as e:
    print(f"JSON 파싱 실패: {e}")