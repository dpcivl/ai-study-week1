import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic

load_dotenv()
client = Anthropic()

# 공개 URL의 이미지 분석
# 예: 위키피디아 이미지
image_url = "https://avatars.githubusercontent.com/u/95332280?v=4"

print(f"이미지 URL 분석: {image_url}")
print("=" * 60)

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
                        "type": "url",
                        "url": image_url
                    }
                },
                {
                    "type": "text",
                    "text": "이 이미지에 무엇이 있는지 한 줄로 설명해줘."
                }
            ]
        }
    ]
)

print(response.content[0].text)