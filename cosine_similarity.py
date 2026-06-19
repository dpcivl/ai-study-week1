import os
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return np.array(response.data[0].embedding)

def cosine_similarity(a, b):
    """두 벡터의 코사인 유사도 계산"""
    # 방법 1: 수식 그대로
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot_product / (norm_a * norm_b)

# ===== 실험: 다양한 텍스트 쌍 유사도 =====
print("=" * 60)
print("코사인 유사도 측정")
print("=" * 60)

# 비교할 텍스트들
test_pairs = [
    # (텍스트1, 텍스트2, 예상)
    ("강아지", "개", "거의 같음 - 동의어"),
    ("강아지", "고양이", "비슷함 - 같은 동물 카테고리"),
    ("강아지", "자동차", "다름 - 다른 카테고리"),
    ("Python 프로그래밍", "파이썬 코딩", "거의 같음 - 같은 의미"),
    ("Python 프로그래밍", "JavaScript 개발", "비슷함 - 같은 분야"),
    ("Python 프로그래밍", "사과 파이 만들기", "다름 - 무관"),
    ("임베디드 시스템", "MCU 펌웨어", "비슷함 - 관련 분야"),
    ("임베디드 시스템", "웹 디자인", "다름 - 다른 분야"),
]

# 임베딩 미리 계산 (캐싱)
all_texts = set()
for t1, t2, _ in test_pairs:
    all_texts.add(t1)
    all_texts.add(t2)

print(f"\n임베딩 계산 중... ({len(all_texts)}개)")
embeddings = {t: get_embedding(t) for t in all_texts}
print("완료\n")

print(f"{'텍스트 1':<25} {'텍스트 2':<25} {'유사도':<10} 예상")
print("-" * 90)

for t1, t2, expected in test_pairs:
    sim = cosine_similarity(embeddings[t1], embeddings[t2])
    print(f"{t1:<25} {t2:<25} {sim:.4f}    {expected}")