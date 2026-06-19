import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# 클라이언트 생성 시 재시도 설정
client = Anthropic(
    max_retries=3,  # 기본값 2.0부터 가능
    timeout=30.0    # 30초 타임아웃
)

# 일반 호출 (SDK가 알아서 재시도)
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[{"role": "user", "content": "재시도 자동인지 확인"}]
)

print(response.content[0].text)

# ===== 호출별로 재시도 설정 변경 =====
# 특정 호출만 더 많이 재시도하고 싶을 때
response = client.with_options(max_retries=5).messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[{"role": "user", "content": "중요한 호출"}]
)