"""
에너지 관리 MCP 서버 (FEMS 워밍업)
가짜 데이터로 FEMS 도메인 도구들 구현
"""
import random
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("energy-management-server")


# ===== 가짜 데이터베이스 =====
# 실제로는 FEMS DB나 API에서 가져옴

FAKE_LINES = {
    "line_1": {"name": "조립 라인 1", "rated_power_kw": 150},
    "line_2": {"name": "조립 라인 2", "rated_power_kw": 200},
    "line 3": {"name": "포장 라인", "rated_power_kw": 80},
    "line_4": {"name": "도장 라인", "rated_power_kw": 250},
}


def generate_fake_consumption(line_id: str, hours: int = 24) -> list:
    """가짜 전력 사용량 생성"""
    if line_id not in FAKE_LINES:
        return []
    
    rated = FAKE_LINES[line_id]["rated_power_kw"]
    now = datetime.now()

    data = []
    for i in range(hours):
        timestamp = now - timedelta(hours=hours - i - 1)
        # 70 ~ 100% 사용률 랜덤
        usage = rated * random.uniform(0.7, 1.0)
        data.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:00"),
            "power_kw": round(usage, 1)
        })

    return data


FAKE_ALARMS = [
    {
        "alarm_id": "A001", 
        "timestamp": "2026-06-25 14:23",
        "line_id": "line_4",
        "severity": "high",
        "message": "도장 라인 전력 사용량 정격 초과 (110%)"
    },
    {
        "alarm_id": "A002",
        "timestamp": "2026-06-25 16:45",
        "line_id": "line_2",
        "severity": "medium",
        "message": "조립 라인 2 전력 효율 저하 감지"
    },
    {
        "alarm_id": "A003",
        "timestamp": "2026-06-25 18:12",
        "line_id": "line_1",
        "severity": "low",
        "message": "조립 라인 1 야간 대기 전력 평소보다 높음"
    },
]


# ===== 도구 1: 라인 목록 =====
@mcp.tool()
def list_production_lines() -> str:
    """
    공장의 모든 생산 라인 목록을 반환합니다. 
    각 라인의 ID, 이름, 정격 전력을 포함합니다. 

    Returns:
        라인 목록 문자열
    """
    lines = []
    for line_id, info in FAKE_LINES.items():
        lines.append(
            f"- {line_id}: {info['name']} (정격: {info['rated_power_kw']}kW)"
        )
    return "생산 라인 목록:\n" + "\n".join(lines)


# ===== 도구 2: 전력 사용량 조회 =====
@mcp.tool()
def get_energy_consumption(line_id: str, hours: int = 24) -> str:
    """
    특정 라인의 최근 전력 사용량을 조회합니다. 
    
    Args:
        line_id: 라인 ID (예: line_1, line_2, line_3, line_4)
        hours: 조회할 과거 시간 범위 (기본 24시간)
        
    Returns:
        시간별 전력 사용량
    """
    if line_id not in FAKE_LINES:
        return f"오류: 알 수 없는 라인 '{line_id}'. list_production_lines로 확인하세요."
    
    line_info = FAKE_LINES[line_id]
    data = generate_fake_consumption(line_id, hours)

    if not data:
        return f"{line_info['name']}: 데이터 없음"
    
    # 통계
    powers = [d['power_kw'] for d in data]
    avg = sum(powers) / len(powers)
    max_power = max(powers)
    min_power = min(powers)

    result = f"{line_info['name']} ({line_id}) - 최근 {hours}시간 \n"
    result += f"정격 전력: {line_info['rated_power_kw']}kW\n"
    result += f"평균: {avg:.1f}kW, 최대: {max_power:.1f}kW, 최소: {min_power:.1f}kW\n\n"

    # 최근 5시간만 상세 표시 (전부면 길어짐)
    result += "최근 5시간 상세:\n"
    for d in data[-5:]:
        result += f"  {d['timestamp']}: {d['power_kw']}kW\n"

    return result



# ===== 도구 3: 알람 조회 =====
@mcp.tool()
def list_alarms(severity: str = "all") -> str:
    """
    현재 발생한 알람 목록을 조회합니다. 
    
    Args:
        severity: 알람 등급 필터 ("high", "medium", "low", "all" 중 하나)
    
    Returns:
        알람 목록
    """
    if severity not in ["high", "medium", "low", "all"]:
        return "오류: severity는 'high', 'medium', 'low', 'all' 중 하나여야 함"
    
    # 필터링
    if severity == "all":
        filtered = FAKE_ALARMS
    else:
        filtered = [a for a in FAKE_ALARMS if a['severity'] == severity]

    if not filtered:
        return f"등급 '{severity}'에 해당하는 알람 없음"
    
    result = f"알람 {len(filtered)}건:\n"
    for alarm in filtered:
        result += (
            f"\n[{alarm['alarm_id']}] {alarm['severity'].upper()}\n"
            f"  시각: {alarm['timestamp']}\n"
            f"  라인: {alarm['line_id']}\n"
            f"  메시지: {alarm['message']}\n"
        )
    
    return result


# ===== 도구 4: 라인 상태 =====
@mcp.tool()
def get_line_status(line_id: str) -> str:
    """
    특정 라인의 현재 운영 상태를 조회합니다. 
    
    Args:
        line_id: 라인 ID
        
    Returns:
        라인 상태 정보
    """
    if line_id not in FAKE_LINES:
        return f"오류: 알 수 없는 라인 '{line_id}"
    
    line_info = FAKE_LINES[line_id]
    rated = line_info['rated_power_kw']

    # 가짜 현재 상태 생성
    current_power = rated * random.uniform(0.6, 1.05)
    is_running = random.random() > 0.1      # 90% 가동 중
    efficiency = random.uniform(0.75, 0.95)

    # 알람 체크
    line_alarms = [a for a in FAKE_ALARMS if a['line_id'] == line_id]

    result = f"{line_info['name']} ({line_id}) 현재 상태\n"
    result += f"  가동 여부: {'운영 중' if is_running else '중단'}\n"
    result += f"  현재 전력: {current_power:.1f}kW (정격 대비 {current_power/rated*100:.1f}%\n)"
    result += f"  효율: {efficiency*100:.1f}%\n"
    result += f"  관련 알람: {len(line_alarms)}건"

    if line_alarms:
        result += "  (list_alarm로 상세 확인)"

    return result


if __name__ == "__main__":
    mcp.run()