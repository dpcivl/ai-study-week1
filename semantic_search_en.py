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

# ===== 한국어 원본을 영어로 번역 =====
# 한국어 버전과 정확히 같은 정보, 같은 길이감으로 번역
documents = [
    "Python is a dynamically-typed interpreted language with high code readability and easy learning curve.",
    "C language is primarily used for system programming and embedded development.",
    "Rust provides memory safety while delivering performance comparable to C/C++.",
    "JavaScript started as a script language running in web browsers.",
    "TypeScript is an extension language that adds static typing to JavaScript.",
    "Go language was created by Google as a compiled language with strong concurrency support.",
    "Swift is a language created by Apple, used for iOS and macOS app development.",
    "Kotlin is a modern language running on JVM, primarily used for Android development.",
    "ARM Cortex-M series are MCUs widely used in low-power embedded systems.",
    "FreeRTOS is an open-source real-time operating system frequently used in embedded systems.",
    "DMA is a technology that transfers data between memory and peripherals without CPU involvement.",
    "I2C and SPI are the most commonly used serial communication protocols in embedded systems.",
]

# ===== 인덱싱 =====
print("Indexing documents...")
doc_embeddings = []
for i, doc in enumerate(documents):
    emb = get_embedding(doc)
    doc_embeddings.append(emb)
    print(f"  {i+1}/{len(documents)} done")

print(f"\nTotal {len(documents)} documents indexed\n")

# ===== 검색 함수 =====
def search(query, top_k=3):
    query_emb = get_embedding(query)
    
    similarities = []
    for i, doc_emb in enumerate(doc_embeddings):
        sim = cosine_similarity(query_emb, doc_emb)
        similarities.append((i, sim))
    
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for i, sim in similarities[:top_k]:
        results.append({
            "rank": len(results) + 1,
            "document": documents[i],
            "similarity": sim,
            "index": i
        })
    return results

# ===== 한국어 질문의 영어 버전 =====
test_queries = [
    "What's a good language for embedded development?",  # 임베디드 개발에 좋은 언어는?
    "How to develop web frontend?",                       # 웹 프론트엔드 개발하려면?
    "Recommend a memory-safe language",                   # 메모리 안전한 언어 추천
    "I want to make iOS apps",                            # iOS 앱 만들고 싶어
    "Protocols for sensor communication",                 # 센서랑 통신할 때 쓰는 프로토콜
]

for query in test_queries:
    print("=" * 70)
    print(f"Query: {query}")
    print("=" * 70)
    
    results = search(query, top_k=3)
    for r in results:
        print(f"\n[Rank {r['rank']}] Similarity: {r['similarity']:.4f}")
        print(f"  {r['document']}")
    
    print()