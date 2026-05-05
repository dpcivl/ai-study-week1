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

    # 매번 새 messages로 호출 (히스토리 안 쌓음)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": user_input }]
    )

    # 응답 추출
    assistant_message = response.content[0].text

    # 응답 출력
    print(f"\nClaude: {assistant_message}\n")

    # # 응답도 히스토리에 추가 (이게 중요!) <- 왜 중요한 거지?
    # messages.append({
    #     "role": "assistant",
    #     "content": assistant_message
    # })