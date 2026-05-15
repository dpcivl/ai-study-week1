import os
import base64
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# 이미지 파일을 base64로 변환
def encode_image(image_path):
    """이미지 파일을 base64 문자열로 인코딩"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")
    

# 이미지 확장자에서 media type 추출
def get_media_type(image_path):
    ext = image_path.lower().split('.')[-1]
    types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp"
    }
    return types.get(ext, "image/jpeg")

# ===== 실험 1: 이미지 분석 =====
image_path = "images/test1.png"  # 본인 이미지 경로로 변경

print(f"이미지 분석: {image_path}")
print("=" * 60)

image_data = encode_image(image_path)
media_type = get_media_type(image_path)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    }
                },
                {
                    "type": "text",
                    "text": "이 이미지를 자세히 분석해줘. 무엇이 보이는지, 어떤 분위기인지, 특이한 점이 있는지."
                }
            ]
        }
    ]
)

print(response.content[0].text)
print(f"\n[Tokens] in: {response.usage.input_tokens}, out: {response.usage.output_tokens}")