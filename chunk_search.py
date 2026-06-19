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

# ===== 긴 문서 (시뮬레이션) =====
long_document = """
# 임베디드 시스템 입문 가이드

## 1장: 임베디드 시스템이란?

임베디드 시스템은 특정 목적을 위해 설계된 컴퓨터 시스템입니다. 
일반 PC와 달리 정해진 기능만 수행하며, 자원(메모리, 전력, 처리 능력)이 
제한적입니다. 우리 주변의 가전제품, 자동차, 의료기기 등 거의 모든 
전자기기에 임베디드 시스템이 들어 있습니다.

## 2장: MCU 선택 기준

마이크로컨트롤러(MCU)를 선택할 때 고려할 요소는 다양합니다. 
첫째, 처리 성능입니다. ARM Cortex-M0는 단순 작업에, M4/M7은 
복잡한 신호처리에 적합합니다. 둘째, 메모리 크기입니다. 
플래시 메모리와 RAM 크기는 펌웨어 크기를 결정합니다. 
셋째, 주변장치 지원입니다. UART, SPI, I2C, ADC 등 필요한 
인터페이스가 있는지 확인해야 합니다.

## 3장: RTOS 도입

실시간 운영체제(RTOS) 도입은 신중히 결정해야 합니다. 
RTOS의 장점은 멀티태스킹, 우선순위 기반 스케줄링, 동기화 
도구 제공입니다. 하지만 추가 메모리 사용(보통 5-10KB)과 
오버헤드가 있습니다. 단순한 폴링 기반 시스템에서는 오히려 
복잡도만 증가시킬 수 있습니다. FreeRTOS가 가장 널리 쓰이며, 
Zephyr는 더 현대적인 대안입니다.

## 4장: 전력 관리

배터리 동작 임베디드 기기에서 전력 관리는 핵심입니다. 
주요 기법으로는 슬립 모드 활용, 클록 주파수 동적 조절(DVFS), 
사용하지 않는 주변장치 게이팅이 있습니다. 측정 도구로 
DMM과 전류 프로파일러를 사용해야 정확한 분석이 가능합니다.

## 5장: 디버깅 도구

임베디드 디버깅은 일반 소프트웨어와 다릅니다. 
JTAG/SWD를 통한 인-서킷 디버깅이 기본입니다. 
J-Link, ST-Link, OpenOCD가 대표적인 디버거입니다. 
로직 애널라이저는 통신 프로토콜 디버깅에 필수입니다. 
오실로스코프는 신호 무결성 확인에 사용됩니다.
"""

# ===== 청크 분할 =====
def split_into_chunks(text, chunk_size=200, overlap=50):
    """
    텍스트를 청크로 분할
    - chunk_size: 청크 크기 (글자 수)
    - overlap: 청크 간 겹치는 부분 (맥락 유지용)
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size - overlap  # overlap만큼 뒤로
    return chunks

chunks = split_into_chunks(long_document, chunk_size=300, overlap=50)
print(f"문서를 {len(chunks)}개 청크로 분할\n")
print("청크 예시:")
for i, chunk in enumerate(chunks[:3]):
    print(f"\n--- 청크 {i+1} ---")
    print(chunk[:150] + "...")

# ===== 임베딩 생성 =====
print("\n\n청크 임베딩 생성 중...")
chunk_embeddings = []
for i, chunk in enumerate(chunks):
    emb = get_embedding(chunk)
    chunk_embeddings.append(emb)

print(f"{len(chunks)}개 청크 인덱싱 완료\n")

# ===== 검색 =====
def search_chunks(query, top_k=3):
    query_emb = get_embedding(query)

    similarities = []
    for i, chunk_emb in enumerate(chunk_embeddings):
        sim = cosine_similarity(query_emb, chunk_emb)
        similarities.append((i, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)

    return [
        {
            "chunk_id": i,
            "chunk": chunks[i],
            "similarity": sim
        }
        for i, sim in similarities[:top_k]
    ]

# ===== 질문 테스트 =====
queries = [
    "RTOS는 언제 도입해야 해?",
    "배터리 절약 방법",
    "어떤 디버거 써야 해?",
    "MCU 고를 때 뭘 봐야 해?",
]

for query in queries:
    print("=" * 70)
    print(f"질문: {query}")
    print("=" * 70)

    results = search_chunks(query, top_k=2)
    for i, r in enumerate(results, 1):
        print(f"\n[{i}위] 청크 {r['chunk_id']+1}, 유사도: {r['similarity']:.4f}")
        print(f"내용: {r['chunk'][:200]}...")
    print()