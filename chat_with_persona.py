import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# 대화 히스토리를 저장할 리스트
messages = []

print("Claude와 대화를 시작합니다. 'quit' 입력 시 종료. \n")

while True:
    # 사용자 입력 받기
    user_input = input("You: ")

    if user_input.lower() == "quit":
        print("대화를 종료합니다.")
        break

    # 사용자 메세지를 히스토리에 추가
    messages.append({
        "role": "user",
        "content": user_input
    })

    # API 호출
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system="""당신은 30년 경력의 임베디드 시스템 시니어 엔지니어입니다. 
        - 답변은 항상 간결하고 정확하게
        - 기술적 트레이드오프 중심으로 설명
        - C/C++, RTOS, MCU 펌웨어 관점에서 답변
        - 메모리, 전력, 실시간성 항상 고려""",
        messages=messages
    )

    # 응답 추출
    assistant_message = response.content[0].text

    # 응답 출력
    print(f"\nClaude: {assistant_message}\n")

    # 토큰 사용량 출력 (추가)
    print(f"[Tokens] input: {response.usage.input_tokens}, "
          f"output: {response.usage.output_tokens}, "
          f"messages 수: {len(messages) + 1}]\n")

    # 응답도 히스토리에 추가 (이게 중요!) <- 왜 중요한 거지?
    messages.append({
        "role": "assistant",
        "content": assistant_message
    })