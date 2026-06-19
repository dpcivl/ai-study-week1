import os
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

def get_embedding(text, model="text-embedding-3-small"):
    """텍스트를 벡터로 변환"""
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

# ===== 실험 1: 임베딩이 어떻게 생겼는지 =====
print("=" * 60)
print("실험 1: 임베딩 = 숫자 리스트")
print("=" * 60)

text = "Python은 프로그래밍 언어입니다."
embedding = get_embedding(text)

print(f"입력 텍스트: {text}")
print(f"임베딩 차원 수: {len(embedding)}")
print(f"앞 10개 값: {embedding[:10]}")
print(f"뒤 5개 값: {embedding[-5:]}")
print(f"전부 0 ~ 1 사이? {min(embedding):.3f} ~ {max(embedding):.3f}")

# ===== 실험 2: 같은 텍스트는 같은 임베딩 =====
print("\n" + "=" * 60)
print("실험 2: 같은 텍스트 두 번 임베딩")
print("=" * 60)

text = "임베디드 개발"
emb1 = get_embedding(text)
emb2 = get_embedding(text)

# numpy로 비교
emb1_np = np.array(emb1)
emb2_np = np.array(emb2)

print(f"emb1[:5]: {emb1[:5]}")
print(f"emb2[:5]: {emb2[:5]}")
print(f"두 임베딩이 같은가? {np.array_equal(emb1_np, emb2_np)}")

# ===== 실험 3: 비슷한 의미는 비슷한 임베딩 =====
print("\n" + "=" * 60)
print("실험 3: 의미가 비슷한 텍스트 비교")
print("=" * 60)

texts = [
    "강아지",
    "개",
    "고양이",
    "자동차",
    "Python 프로그래밍",
    "파이썬 코딩"
]

print("각 텍스트를 임베딩으로 변환:")
embeddings = {}
for text in texts:
    emb = get_embedding(text)
    embeddings[text] = np.array(emb)
    print(f"  '{text}' -> 1536차원 벡터")

print("\n앞 5개 값이 유사한지 비교:")
for text, emb in embeddings.items():
    print(f"  {text}: {emb[:5]}")