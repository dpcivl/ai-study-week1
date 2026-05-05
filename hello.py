import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

message = client.messages.create(
    model="claude-haiku-4-5-20251001",  # 가장 저렴, 학습용 충분
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "임베디드 개발자가 AI Agent 분야로 전환할 때 가장 큰 강점이 뭘까?"}
    ]
)

print(message.content[0].text)
print(f"\n--- 사용량 ---")
print(f"Input tokens: {message.usage.input_tokens}")
print(f"Output tokens: {message.usage.output_tokens}")