import os
import anthropic
from anthropic import Anthropic  # 위에서 anthropic 임포트 했는데 왜 또 임포트? anthropic으로 임포트 하면 anthropic.Anthropic()으로 호출해야 함
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# ===== 실험 1: 정상 케이스 =====
print("=" * 60)
print("실험 1: 정상 호출")
print("=" * 60)

try:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": "안녕"}]
    )
    print(f"성공: {response.content[0].text}")
except Exception as e:
    print(f"실패: {e}")

# ===== 실험 2: 인증 에러 (의도적으로) =====
print("\n" + "=" * 60)
print("실험 2: 잘못된 API 키")
print("=" * 60)

# 일부러 잘못된 키로 클라이언트 생성
bad_client = Anthropic(api_key="sk-ant-invalid-key-12345")

try:
    response = bad_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": "안녕"}]
    )
except anthropic.AuthenticationError as e:
    print(f"인증 에러 잡힘!")
    print(f"  타입: {type(e).__name__}")
    print(f"  메시지: {e}")
    print(f"  -> 해결: API 키 확인")

# ===== 실험 3: 잘못된 모델 이름 =====
print("\n" + "=" * 60)
print("실험 3: 존재하지 않는 모델")
print("=" * 60)

try:
    response = client.messages.create(
        model="claude-superintelligent-9000",
        max_tokens=100,
        messages=[{"role": "user", "content": "안녕"}]
    )
except anthropic.NotFoundError as e:
    print(f"NotFoundError 잡힘!")
    print(f"  메시지: {e}")
except anthropic.BadRequestError as e:
    print(f"BadRequestError 잡힘!")
    print(f"  메시지: {e}")

# ===== 실험 4: 잘못된 요청 형식 =====
print("\n" + "=" * 60)
print("실험 4: 빈 messages")
print("=" * 60)

try:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[]  # 빈 배열 - 잘못된 요청
    )
except anthropic.BadRequestError as e:
    print(f"BadRequestError 잡힘!")
    print(f"  메시지: {e}")

# ===== 실험 5: 종합 에러 핸들러 패턴 =====
print("\n" + "=" * 60)
print("실험 5: 실전 에러 핸들러 패턴")
print("=" * 60)

def safe_llm_call(messages, model="claude-haiku-4-5-20251001"):
    """실전에서 사용하는 안전한 LLM 호출 함수"""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=messages
        )
        return {
            "success": True,
            "text": response.content[0].text,
            "usage": response.usage
        }
    
    except anthropic.RateLimitError as e:
        # 일시적 - 재시도 권장
        return {
            "success": False,
            "error_type": "rate_limit",
            "message": "호출 한도 초과. 잠시 후 재시도하세요.",
            "retryable": True
        }
    
    except anthropic.APITimeoutError as e:
        # 일시적 - 재시도 권장
        return {
            "success": False,
            "error_type": "timeout",
            "message": "응답 시간 초과", 
            "retryable": True
        }
    
    except anthropic.APIConnectionError as e:
        # 일시적 - 재시도 권장
        return {
            "success": False,
            "error_type": "connection",
            "message": "네트워크 연결 실패",
            "retryable": True
        }
    
    except anthropic.AuthenticationError as e:
        # 영구적 - 재시도 무의미
        return  {
            "success": False,
            "error_type": "auth",
            "message": "API 키 확인 필요",
            "retryable": False
        }
    
    except anthropic.BadRequestError as e:
        # 영구적 - 코드 수정 필요
        return {
            "success": False,
            "error_type": "bad_request",
            "message": str(e),
            "retryable": False
        }
    
    except anthropic.APIError as e:
        # 기타 API 에러
        return {
            "success": False,
            "error_type": "api_error",
            "message": str(e),
            "retryable": False
        }
    
    except Exception as e:
        # 예상 못 한 에러
        return {
            "success": False,
            "error_type": "unknown",
            "message": str(e),
            "retryable": False
        }
    
# 사용 예
result = safe_llm_call([{"role": "user", "content": "Python에서 리스트와 튜플 차이"}])
if result["success"]:
    print(f"성공: {result['text'][:100]}...")
else:
    print(f"실패 ({result['error_type']}): {result['message']}")
    print(f"재시도 가능: {result['retryable']}")