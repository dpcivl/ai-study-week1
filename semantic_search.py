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
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# ===== 문서 데이터베이스 (가짜) =====
documents = [
    "Python은 동적 타입 인터프리터 언어로, 코드 가독성이 높고 배우기 쉽습니다.",
    "C 언어는 시스템 프로그래밍과 임베디드 개발에 주로 사용됩니다.",
    "Rust는 메모리 안전성을 보장하면서도 C/C++ 수준의 성능을 제공합니다.",
    "JavaScript는 웹 브라우저에서 실행되는 스크립트 언어로 시작했습니다.",
    "TypeScript는 JavaScript에 정적 타입을 추가한 확장 언어입니다.",
    "Go 언어는 Google이 만든 컴파일 언어로, 동시성 처리에 강점이 있습니다.",
    "Swift는 Apple이 만든 언어로 iOS와 macOS 앱 개발에 사용됩니다.",
    "Kotlin은 JVM 위에서 실행되는 현대적인 언어로 Android 개발에 주로 쓰입니다.",
    "ARM Cortex-M 시리즈는 저전력 임베디드 시스템에 널리 사용되는 MCU입니다.",
    "FreeRTOS는 오픈소스 실시간 운영체제로 임베디드 시스템에서 자주 사용됩니다.",
    "DMA는 CPU 없이 메모리와 주변장치 간 데이터를 전송하는 기술입니다.",
    "I2C와 SPI는 임베디드 시스템에서 가장 흔히 사용되는 시리얼 통신 프로토콜입니다.",
]

# ===== 인덱싱: 모든 문서의 임베딩 계산 =====
print("문서 인덱싱 중...")
doc_embeddings = []
for i, doc in enumerate(documents):
    emb = get_embedding(doc)
    doc_embeddings.append(emb)
    print(f"  {i+1}/{len(documents)} 완료")

print(f"\n총 {len(documents)}개 문서 인덱싱 완료")
print(f"각 문서는 1536차원 벡터로 변환됨\n")

# ===== 검색 함수 =====
def search(query, top_k=3):
    """질문에 가장 유사한 문서 top_k개 찾기"""
    # 1. 질문을 임베딩으로 
    query_emb = get_embedding(query)

    # 2. 모든 문서와 유사도 계산
    similarities = []
    for i, doc_emb in enumerate(doc_embeddings):
        sim = cosine_similarity(query_emb, doc_emb)
        similarities.append((i, sim))

    # 3. 유사도 높은 순으로 정렬
    similarities.sort(key=lambda x: x[1], reverse=True)

    # 4. 상위 K개 반환
    results = []
    for i, sim in similarities[:top_k]:
        results.append({
            "rank": len(results) + 1,
            "document": documents[i],
            "similarity": sim,
            "index": i
        })
    return results

# ===== 검색 테스트 =====
test_queries = [
    "임베디드 개발에 좋은 언어는?",
    "웹 프론트엔드 개발하려면?",
    "메모리 안전한 언어 추천",
    "iOS 앱 만들고 싶어",
    "센서랑 통신할 때 쓰는 프로토콜",
]

for query in test_queries:
    print("=" * 70)
    print(f"질문: {query}")
    print("=" * 70)

    results = search(query, top_k=3)
    for r in results:
        print(f"\n[{r['rank']}위] 유사도: {r['similarity']:.4f}")
        print(f"  {r['document']}")

    print()