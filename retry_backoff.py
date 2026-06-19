import os
import time
import random
import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def call_with_retry(
        messages,
        model="claude-haiku-4-5-20251001",
        max_retries=5,
        base_delay=1.0,
        max_delay=60.0
):
    """
    Exponential backoff + jitter로 재시도
    
    max_retries: 최대 재시도 횟수
    base_delay: 첫 지연 (초)
    max_delay: 최대 지연 (초)
    """

    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=messages
            )
            # 성공
            if attempt > 0:
                print(f"  -> {attempt+1}번째 시도에서 성공")
            return response
        
        except (
            anthropic.RateLimitError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError
        ) as e:
            # 재시도 가능한 에러
            last_error = e

            if attempt == max_retries -1:
                # 마지막 시도였음
                print(f"  -> 모든 재시도 실패 ({max_retries}회)")
                raise

            # Exponential backoff + jitter 계산
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # 10% jitter
            total_delay = delay + jitter

            print(f"  -> 시도 {attempt+1} 실패 ({type(e).__name__})")
            print(f"  -> {total_delay:.1f}초 후 재시도...")
            time.sleep(total_delay)

        except Exception as e:
            # 재시도 불가능한 에러
            print(f"  -> 재시도 불가능한 에러: {type(e).__name__}")
            raise

    raise last_error

# ===== 사용 예시 =====
print("=" * 60)
print("재시도 로직 테스트")
print("=" * 60)

try:
    response = call_with_retry(
        messages=[{"role": "user", "content": "재시도 패턴이 뭐야?"}]
    )
    print(f"\n응답: {response.content[0].text[:200]}...")
except Exception as e:
    print(f"\n최종 실패: {e}")

# ===== 재시도 패턴 시뮬레이션 =====
print("\n" + "=" * 60)
print("Exponential Backoff 시뮬레이션 (실제 호출 X)")
print("=" * 60)

print("\nbase_delay=1.0, 5번 재시도 시 대기 시간:")
for attempt in range(5):
    delay = min(1.0 * (2 ** attempt), 60.0)
    jitter = delay * 0.05  # 평균값으로 표시
    total = delay + jitter
    print(f"  시도 {attempt+1}: {delay:.1f}초 + jitter = {total:.1f}초")

# 누적 시간 계산
total_wait = sum(min(1.0 * (2 ** i), 60.0) for i in range(5))
print(f"\n총 대기 시간 (최악): {total_wait:.1f}초")