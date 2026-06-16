import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

SYSTEM_PROMPT = """당신은 임베디드 시스템 전문가입니다. 

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

messages = []
total_cache_read = 0
total_cache_write = 0
total_normal = 0
turn = 0

print("캐싱 활성화 챗봇. 'quit' 종료, 'stats' 통계.\n")

while True:
    user_input = input("You: ")
    
    if user_input.lower() == "quit":
        break
    
    if user_input.lower() == "stats":
        print(f"\n=== 통계 ===")
        print(f"Cache write: {total_cache_write}")
        print(f"Cache read: {total_cache_read}")
        print(f"Normal input: {total_normal}")
        
        # 캐싱 안 썼다면 들었을 비용
        no_cache_input = total_cache_write + total_cache_read + total_normal
        cost_no_cache = no_cache_input / 1_000_000 * 1.0
        
        # 실제 비용
        cost_with_cache = (
            total_normal / 1_000_000 * 1.0 +
            total_cache_write / 1_000_000 * 1.25 +
            total_cache_read / 1_000_000 * 0.10
        )
        
        print(f"\n비용:")
        print(f"  캐싱 없었다면: ${cost_no_cache:.6f}")
        print(f"  실제 비용:    ${cost_with_cache:.6f}")
        print(f"  절감:         ${cost_no_cache - cost_with_cache:.6f}")
        if cost_no_cache > 0:
            print(f"  절감률:       {(cost_no_cache - cost_with_cache) / cost_no_cache * 100:.1f}%\n")
        continue
    
    turn += 1
    messages.append({"role": "user", "content": user_input})
    
    # 시스템 프롬프트에 캐싱 적용
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=messages
    )
    
    assistant_text = response.content[0].text
    print(f"\nClaude: {assistant_text}")
    
    # 토큰 집계
    usage = response.usage
    cache_write = getattr(usage, 'cache_creation_input_tokens', 0) or 0
    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
    normal = usage.input_tokens
    
    total_cache_write += cache_write
    total_cache_read += cache_read
    total_normal += normal
    
    print(f"\n[Turn {turn}] normal: {normal}, "
          f"cache_write: {cache_write}, cache_read: {cache_read}\n")
    
    messages.append({"role": "assistant", "content": assistant_text})