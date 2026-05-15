import os
import base64
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")
    
# 와이어프레임 사진 경로
wireframe_path = "images/wireframe.png"

print("손그림 와이어프레임 -> HTML 변환")
print("=" * 60)

# Sonnet으로! 이런 작업은 Haiku보다 Sonnet이 좋음
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": encode_image(wireframe_path)
                    }
                },
                {
                    "type": "text",
                    "text": """이 손그림 와이어프레임을 보고 작동하는 HTML 페이지를 만들어줘. 
                    
                    요구사항: 
                    1. 단일 HTML 파일 (인라인 CSS)
                    2. 모던하고 깔끔한 디자인 (Tailwind 같은 느낌, 단 CDN 안 쓰고 vanilla CSS로)
                    3. 반응형
                    4. 와이어프레임의 레이아웃 충실히 재현
                    5. 색상은 차분한 모던 톤
                    6. 텍스트가 명시 안 된 부분은 자연스러운 placeholder 사용
                    
                    코드만 출력. 설명 X. """
                }
            ]
        }
    ]
)

html_code = response.content[0].text
# HTML 코드 블록 제거 (LLM이 ```html으로 감쌌을 수도)
if html_code.startswith("```"):
    lines = html_code.split('\n')
    html_code = '\n'.join(lines[1:-1])

# 파일로 저장
output_path = "wireframe_result.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_code)

print(f"\nHTML 생성 완료: {output_path}")
print(f"파일 크기: {len(html_code)} 글자")
print(f"\nToken 사용량:")
print(f"  Input: {response.usage.input_tokens}")
print(f"  Output: {response.usage.output_tokens}")

# 비용 계산 (Sonnet 4.6 가격 가정: $3/M input, $15/M output)
cost = (
    response.usage.input_tokens / 1_000_000 * 3 +
    response.usage.output_tokens / 1_000_000 * 15
)
print(f"  비용: ${cost:.4f} (약 {cost * 1400:.2f}원)")

print(f"\n브라우저로 열기: file:///{os.path.abspath(output_path)}")