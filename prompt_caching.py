import os
import time
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# 긴 시스템 프롬프트 (캐싱 효과 보려면 1024 토큰 이상 필요) - 왜 1024 토큰 이상 필요??? 캐싱 쓰려고. 근데 4096 이상이 필요함.
long_system = """당신은 임베디드 시스템 전문가입니다. 

전문 분야:
- ARM Cortex-M 시리즈 (M0/M3/M4/M7) 아키텍처
- STM32, ESP32, Nordic nRF 시리즈 MCU
- FreeRTOS, Zephyr RTOS, ThreadX 운영체제
- C/C++ 펌웨어 개발 (저수준 + 고수준)
- 통신 프로토콜: UART, SPI, I2C, CAN, USB, BLE, WiFi
- 디버깅 도구: J-Link, ST-Link, OpenOCD, GDB
- 전력 관리: Sleep modes, DVFS, peripheral gating
- 메모리 관리: 스택/힙 사이징, DMA, 메모리 맵
- 부트로더 설계 및 펌웨어 업데이트 (OTA)
- 실시간 시스템 설계: 데드라인, 우선순위 역전, 인터럽트 처리

답변 원칙:
1. 기술적으로 정확하고 검증 가능한 정보만 제공
2. 구체적인 칩셋/제품명을 예시로 들어 설명
3. 코드 예제는 항상 동작 가능한 완전한 코드로 제공
4. 트레이드오프를 명확히 설명 (장점만 나열하지 않음)
5. 메모리 사용량, 전력 소비, 실시간 성능 영향을 항상 고려
6. 안전 임계 시스템(safety-critical)에서의 주의사항 포함

응답 형식:
- 짧고 명확한 답변 우선
- 필요시 코드 블록 포함
- 깊이 있는 설명이 필요하면 단계별로 구조화
- 가독성을 위해 적절한 마크다운 사용

당신은 30년 경력을 가진 시니어 임베디드 엔지니어로 답변하세요. 
""" * 7 # 더 길게 만들기 위해 반복

questions = [
    "Cortex-M4와 M7의 가장 큰 차이가 뭐야?",
    "FreeRTOS에서 우선순위 역전 어떻게 방지해?",
    "STM32에서 DMA 사용할 때 주의사항은?",
]

# ===== 실험 A: 캐싱 없음 =====
print("=" * 60)
print("실험 A: 캐싱 없음 - 매번 시스템 프롬프트 처리")
print("=" * 60)

total_input_a = 0
total_time_a = 0

for i, q in enumerate(questions, 1):
    start = time.time()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=long_system, # 일반 string으로 전달 (캐싱 x)
        messages=[{"role": "user", "content": q}]
    )

    elapsed = time.time() - start
    total_time_a += elapsed
    total_input_a += response.usage.input_tokens

    print(f"\n질문 {i}: {q[:30]}...")
    print(f"  Input tokens: {response.usage.input_tokens}")
    print(f"  소요 시간: {elapsed:.2f}초")

print(f"\n[A 합계]")
print(f"  총 input tokens: {total_input_a}")
print(f"  총 시간: {total_time_a:.2f}초")
print(f"  비용 추정: ${total_input_a / 1_000_000 * 1.0:.4f}")

# ===== 실험 B: 캐싱 사용 =====
print("\n\n" + "=" * 60)
print("실험 B: 캐싱 사용 - 시스템 프롬프트 캐싱")
print("=" * 60)

total_input_b = 0
total_cache_write_b = 0
total_cache_read_b = 0
total_time_b = 0

for i, q in enumerate(questions, 1):
    start = time.time()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": long_system,
                "cache_control": {"type": "ephemeral"}  # 이게 캐싱 마커. 찾아보니까 "일시적인"이라는 뜻임
            }
        ],
        messages=[{"role": "user", "content": q}]
    )

    elapsed = time.time() - start
    total_time_b += elapsed

    # 토큰 정보 추출
    usage = response.usage
    cache_write = getattr(usage, 'cache_creation_input_tokens', 0) or 0
    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
    normal_input = usage.input_tokens

    total_input_b += normal_input
    total_cache_write_b += cache_write
    total_cache_read_b += cache_read

    print(f"\n질문 {i}: {q[:30]}...")
    print(f"  Normal input: {normal_input}")
    print(f"  Cache write: {cache_write}")
    print(f"  Cache read: {cache_read}")
    print(f"  소요 시간: {elapsed:.2f}초")

# 비용 계산
cost_b = (
    total_input_b / 1_000_000 * 1.0 +
    total_cache_write_b / 1_000_000 * 1.25 +
    total_cache_read_b / 1_000_000 * 0.10
)

print(f"\n[B 합계]")
print(f"  Normal input: {total_input_b}")
print(f"  Cache write: {total_cache_write_b}")
print(f"  Cache read: {total_cache_read_b}")
print(f"  총 시간: {total_time_b:.2f}초")
print(f"  비용 추정: ${cost_b:.4f}")

# ===== 비교 ======
print("\n\n" + "=" * 60)
print("비교")
print("=" * 60)
cost_a = total_input_a / 1_000_000 * 1.0
savings = (cost_a - cost_b) / cost_a * 100 if cost_a > 0 else 0
time_savings = (total_time_a - total_time_b) / total_time_a * 100 if total_time_a > 0 else 0

print(f"비용:")
print(f"  A (캐싱 X): ${cost_a:.4f}")
print(f"  B (캐싱 O): ${cost_b:.4f}")
print(f"  절감률: {savings:.1f}%")
print(f"\n시간:")
print(f"  A: {total_time_a:.2f}초")
print(f"  B: {total_time_b:.2f}초")
print(f"  절감률: {time_savings:.1f}%")