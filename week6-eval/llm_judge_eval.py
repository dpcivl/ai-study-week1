"""
LLM-as-Judge eval
답변 품질을 다른 LLM이 평가
"""
import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()


# ===== 평가할 답변들 (질문 + 답변 쌍) =====
qa_pairs = [
    {
        "question": "RAG가 뭐야?",
        "answer": "RAG는 Retrieval-Augmented Generation의 약자로, 검색으로 관련 문서를 찾아 LLM 컨텍스트에 추가한 뒤 답변을 생성하는 기법입니다. LLM의 지식 한계를 외부 데이터로 보완합니다."
    },
    {
        "question": "RAG가 뭐야?",
        "answer": "RAG는 좋은 기술입니다. 많이 쓰입니다."  # 부실한 답변
    },
    {
        "question": "파이썬 리스트와 튜플 차이는?",
        "answer": "리스트는 변경 가능(mutable)하고 튜플은 변경 불가능(immutable)합니다. 리스트는 []로, 튜플은 ()로 만듭니다. 튜플이 약간 더 빠르고 메모리 효율적이라 변하지 않는 데이터에 적합합니다."
    },
    {
        "question": "파이썬 리스트와 튜플 차이는?",
        "answer": "둘 다 데이터를 담는 자료구조입니다."  # 불완전한 답변
    },
]


def judge_answer(question, answer):
    """LLM이 답변 품질을 평가"""

    judge_prompt = f"""당신은 답변 품질을 평가하는 전문가입니다. 

다음 질문과 답변을 평가하세요. 

질문: {question}
답변: {answer}

다음 기준으로 1~10점 평가하고, 반드시 아래 JSON 형식으로만 응답하세요:

{{
    "accuracy": <정확성 1-10>,
    "completeness": <완결성 1-10>,
    "clarity": <명확성 1-10>,
    "overall": <종합 1-10>,
    "reason": "<평가 이유 한 문장>"
}}

다른 텍스트 없이 JSON만 출력하세요."""
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": judge_prompt}]
    )

    text = response.content[0].text

    # JSON 추출
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except Exception as e:
        return {"error": str(e), "raw": text}
    

def run_judge_eval():
    print("=" * 70)
    print("LLM-as-Judge 평가")
    print("=" * 70)

    results = []

    for i, qa in enumerate(qa_pairs, 1):
        question = qa["question"]
        answer = qa["answer"]

        print(f"\n{i}. 질문: {question}")
        print(f"  답변: {answer[:60]}...")

        evaluation = judge_answer(question, answer)

        if "error" in evaluation:
            print(f"  평가 실패: {evaluation['error']}")
            continue

        print(f"  평가:")
        print(f"    정확성: {evaluation['accuracy']}/10")
        print(f"    완결성: {evaluation['completeness']}/10")
        print(f"    명확성: {evaluation['clarity']}/10")
        print(f"    종합: {evaluation['overall']}/10")
        print(f"    이유: {evaluation['reason']}")

        results.append({
            "question": question,
            "answer": answer,
            "evaluation": evaluation
        })

    # 평균 계산
    print("\n" + "=" * 70)
    print("종합 통계")
    print("=" * 70)

    valid_results = [r for r in results if "error" not in r["evaluation"]]
    if valid_results:
        avg_overall = sum(r["evaluation"]["overall"] for r in valid_results) / len(valid_results)
        print(f"평균 종합 점수: {avg_overall:.1f}/10")

    # 저장
    with open("judge_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: judge_results.json")


if __name__ == "__main__":
    run_judge_eval()