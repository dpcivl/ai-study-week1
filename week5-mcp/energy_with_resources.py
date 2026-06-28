"""
MCP 서버 with Tools + Resources
어제 energy_mcp_server.py에 Resources 추가
"""
import random
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("energy-management-v2")


# ===== 가짜 데이터 =====
FAKE_LINES = {
    "line_1": {"name": "조립 라인 1", "rated_power_kw": 150},
    "line_2": {"name": "조립 라인 2", "rated_power_kw": 200},
    "line_3": {"name": "포장 라인", "rated_power_kw": 80},
    "line_4": {"name": "도장 라인", "rated_power_kw": 250},
}


def generate_fake_comsumption(line_id: str, hours: int = 24):
    if line_id not in FAKE_LINES:
        return []
    rated = FAKE_LINES[line_id]["rated_power_kw"]
    now = datetime.now()
    data = []
    for i in range(hours):
        timestamp = now - timedelta(hours=hours - i - 1)
        usage = rated * random.uniform(0.7, 1.0)
        data.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:00"),
            "power_kw": round(usage, 1)
        })
    return data


# ===== Tools (LLM이 호출) =====
@mcp.tool()
def list_production_lines() -> str:
    """생산 라인 목록 조회."""
    lines = []
    for line_id, info in FAKE_LINES.items():
        lines.append(f"- {line_id}: {info['name']} ({info['rated_power_kw']}kW)")
    return "생산 라인:\n" + "\n".join(lines)


@mcp.tool()
def get_energy_consumption(line_id: str, hours: int = 24) -> str:
    """특정 라인의 최근 전력 사용량 조회."""
    if line_id not in FAKE_LINES:
        return f"오류: 알 수 없는 라인 '{line_id}"
    
    data = generate_fake_comsumption(line_id, hours)
    if not data:
        return "데이터 없음"
    
    powers = [d['power_kw'] for d in data]
    avg = sum(powers) / len(powers)

    return (
        f"{FAKE_LINES[line_id]['name']} ({hours}시간)\n"
        f"평균: {avg:.1f}kW, 최대: {max(powers):.1f}kW, 최소: {min(powers):.1f}kW"
    )


# ===== Resources (클라이언트가 미리 가져옴) =====

@mcp.resource("config://operating-rules")
def get_operating_rules() -> str:
    """
    공장 운영 규정 (모든 분석에 자동 적용되어야 하는 규칙)
    """
    return """공장 운영 규정 v2.1:
    
1. 전력 사용 제한
   - 피크 시간대 (10:00-18:00): 정격의 90% 이하 유지
   - 야간 (22:00-06:00): 정격의 30% 이하 유지
   - 위반 시 자동 알람 발생
   
2. 안전 임계값
   - 단일 라인 정격 110% 초과: 즉시 차단
   - 전체 공장 총 전력 1000kW 초과: 부하 분산

3. 보고 의무
   - 일일 보고: 매일 09:00
   - 주간 보고: 매주 월요일
   - 비정상 사용 시 즉시 보고

4. 에너지 절감 정책
   - 휴게시간 (12:00-13:00): 비필수 라인 대기 모드
   - 휴일/주말: 최소 운영

5. 데이터 보존
   - 분당 데이터: 30일 보존
   - 시간당 데이터: 1년 보존
   - 일별 데이터: 영구 보존
    """


@mcp.resource("config://line-specifications")
def get_line_specifications() -> str:
    """
    생산 라인 상세 사양 (참고 데이터)
    """
    specs = ["생산 라인 상세 사양:\n"]
    for line_id, info in FAKE_LINES.items():
        specs.append(
            f"\n{line_id}: {info['name']}\n"
            f"  - 정격 전력: {info['rated_power_kw']}kW\n"
            f"  - 안전 임계: {info['rated_power_kw'] * 1.1:.0f}kW (110%)\n"
            f"  - 효율 목표: 85% 이상 \n"
        )
    return "".join(specs)



@mcp.resource("manual://troubleshooting-guide")
def get_troubleshooting_guide() -> str:
    """
    트러블슈팅 가이드 (문제 해결 매뉴얼)
    """
    return """트러블슈팅 가이드 v1.5:

[전력 과다 사용 시]
1. 해당 라인의 가동 상태 확인 (get_line_status)
2. 정격 대비 사용률 계산
3. 110% 초과면 즉시 운영팀 연락
4. 80~110%는 모니터링 강화

[알람 발생 시]
1. 알람 등급 확인 (high/medium/low)
2. high: 즉시 대응, medium: 1시간 내, low: 일일 점검
3. 관련 라인 상태 확인
4. 운영 로그 검토

[데이터 이상 시]
1. 센서 통신 상태 확인
2. 최근 24시간 데이터 패턴 분석
3. 비교: 정상 패턴 vs 현재 패턴
4. 이상 지속 시 IT팀 연락

[효율 저하 시]
1. 라인별 효율 비교
2. 시간대별 패턴 확인
3. 정비 이력 검토
4. 정비 계획 수립
"""


# ===== Prompts (사용자가 명시 트리거) =====

@mcp.prompt()
def daily_analysis_prompt(date: str = "today") -> str:
    """
    일별 에너지 분석 프롬프트. 
    사용자가 /daily_analysis 입력 시 사용
    """
    return f"""다음 절차로 {date}의 에너지 사용을 분석하세요:

1. list_production_lines로 라인 목록 확인
2. 각 라인의 get_energy_consumption (24시간) 호출
3. config://operating-rules 참조하여 규정 위반 여부 확인
4. 다음 형식으로 보고:
   - 라인별 평균/최대 전력
   - 규정 위반 사항
   - 개선 권고사항

전문적이지만 이해하기 쉽게 작성하세요."""


@mcp.prompt()
def alarm_response_prompt(alarm_id: str) -> str:
    """알람 대응 프롬프트."""
    return f"""알람 {alarm_id} 대응 절차:

1. manual://troubleshooting-guide 참조
2. 알람 발생 라인 식별
3. 해당 라인의 현재 상태 + 최근 사용량 조회
4. config://operating-rules 위반 여부 확인
5. 대응 방안 제시

긴급도 평가 + 구체적 액션 아이템 포함."""


if __name__ == "__main__":
    mcp.run()