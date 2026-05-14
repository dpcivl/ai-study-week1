import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# 실험 1: LLM에게 계산 시키기
print("=" * 60)
print("실험 1: LLM에게 직접 계산 시키기")
print("=" * 60)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[
        {"role": "user", "content": "847 * 2391의 정확한 값은?"}
    ]
)

print(response.content[0].text)
# 정답: 2,025,177
# LLM은 종종 틀린 답을 줌

# 실험 2: 현재 시간 물어보기
print("\n" + "=" * 60)
print("실험 2: LLM에게 현재 시간 물어보기")
print("=" * 60)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[
        {"role": "user", "content": "지금 한국 시간 몇 시야?"}
    ]
)

print(response.content[0].text)
# LLM은 현재 시간 모름. 학습 시점의 정보만 있음

# 실험 3: 실시간 데이터
print("\n" + "=" * 60)
print("실험 3: 실시간 데이터 (오늘 비트코인 가격)")
print("=" * 60)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[
        {"role": "user", "content": "오늘 비트코인 가격이 얼마야?"}
    ]
)

print(response.content[0].text)
# 모름. 학습 시점 이후 데이터 없음