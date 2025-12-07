"""실시간 거래 추천 스크립트 - 현재 시점의 거래 결정 추천"""

import argparse
import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# 로깅 설정 (ERROR 레벨로 모든 로그 억제)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# noisy 로거들 완전히 비활성화
logging.getLogger('httpx').setLevel(logging.CRITICAL)
logging.getLogger('httpcore').setLevel(logging.CRITICAL)
logging.getLogger('services').setLevel(logging.CRITICAL)
logging.getLogger('redisvl').setLevel(logging.CRITICAL)
logging.getLogger('finmem').setLevel(logging.CRITICAL)
logging.getLogger('services.loader').setLevel(logging.CRITICAL)

from config import settings
from services.simulation import SimulationService
from services.backtest import BacktestService


async def main():
    parser = argparse.ArgumentParser(description="실시간 거래 추천")
    parser.add_argument("--ticker", type=str, required=True, help="티커 심볼 (예: AAPL)")
    parser.add_argument("--window", type=int, default=30, help="슬라이딩 윈도우 길이 (기본: 30)")
    parser.add_argument("--interval", type=str, default="1h", help="시간 간격 (예: 1h, 1day)")
    parser.add_argument("--seed", type=int, default=None, help="랜덤 시드")
    parser.add_argument("--use-memory", action="store_true", default=False, help="메모리 학습 사용")
    parser.add_argument("--no-memory", action="store_true", default=False, help="메모리 학습 미사용")
    parser.add_argument("--capital", type=float, default=10000.0, help="초기 자본 (기본: $10,000)")

    args = parser.parse_args()

    # 메모리 사용 여부 결정
    use_memory = args.use_memory or not args.no_memory

    print("=" * 80)
    print(f"실시간 거래 추천 시작: {args.ticker}")
    print(f"현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"윈도우: {args.window}, 간격: {args.interval}")
    print(f"메모리 학습: {'사용' if use_memory else '미사용'}")
    print(f"초기 자본: ${args.capital:,.2f}")
    print("=" * 80)

    try:
        # 서비스 초기화
        sim_service = SimulationService(settings)
        service = BacktestService(sim_service, settings)

        # 현재 시점 거래 추천 실행
        print(f"\n[분석 중] {args.ticker} 데이터를 가져오는 중...\n", flush=True)

        result = await service.run_point(
            ticker=args.ticker,
            window=args.window,
            target_datetime=None,  # None = 현재 시점
            interval=args.interval,
            seed=args.seed,
            use_memory=use_memory,
            shares=1.0,
            initial_capital=args.capital,
        )

        # 결과 출력
        summary = result.summary

        # 디버깅 모드 (필요시 활성화)
        # import json
        # print("\n[DEBUG] Summary 구조:")
        # print(json.dumps(summary, indent=2, default=str))

        decision = summary.get("decision", {})
        bull = summary.get("bull", {})
        bear = summary.get("bear", {})
        report = summary.get("report", {})
        reflection_data = summary.get("reflection", {})
        snapshot = summary.get("snapshot", {})
        latest = snapshot.get("latest", {})

        # 결정 파싱
        if isinstance(decision, dict):
            action = decision.get("action", "HOLD")
            trader_rationale = decision.get("rationale", "")
            confidence = decision.get("confidence", "")
        else:
            action = str(decision) if decision else "HOLD"
            trader_rationale = ""
            confidence = ""

        # Manager의 최종 전략 (있으면 이게 최종 결정)
        manager_strategy = report.get("strategy", "")

        # Manager가 여러 옵션을 제시한 경우 (예: "SELL_25|SELL_50|HOLD") 첫 번째 선택
        if manager_strategy and "|" in manager_strategy:
            manager_options = [opt.strip() for opt in manager_strategy.split("|")]
            manager_strategy = manager_options[0]  # 첫 번째 옵션 선택

        final_action = manager_strategy if manager_strategy else action

        # 추천 근거 구성 - 상세하게 작성
        reasoning_lines = []

        # 1. 현재 시장 상황
        if latest:
            current_price = latest.get("close", 0)
            rsi = latest.get("rsi_14", 0)
            sma_20 = latest.get("sma_20", 0)
            sma_50 = latest.get("sma_50", 0)
            bb_upper = latest.get("bb_upper", 0)
            bb_lower = latest.get("bb_lower", 0)
            bb_middle = latest.get("bb_middle", 0)

            reasoning_lines.append("【시장 현황】")

            # RSI 분석
            if rsi < 30:
                rsi_status = "과매도 구간"
            elif rsi > 70:
                rsi_status = "과매수 구간"
            else:
                rsi_status = "중립 구간"

            reasoning_lines.append(f"현재가: ${current_price:.2f}, RSI: {rsi:.1f} ({rsi_status})")

            # 이평선 분석
            if current_price > sma_20 and sma_20 > sma_50:
                trend = "강한 상승 추세"
            elif current_price < sma_20 and sma_20 < sma_50:
                trend = "강한 하락 추세"
            elif current_price > sma_20:
                trend = "단기 상승 추세"
            elif current_price < sma_20:
                trend = "단기 하락 추세"
            else:
                trend = "횡보 추세"

            reasoning_lines.append(f"이평선: {trend} (20일선: ${sma_20:.2f}, 50일선: ${sma_50:.2f})")

            # 볼린저밴드
            if bb_upper and bb_lower:
                if current_price > bb_upper:
                    bb_status = "상단 돌파 (과매수 신호)"
                elif current_price < bb_lower:
                    bb_status = "하단 이탈 (과매도 신호)"
                elif current_price > bb_middle:
                    bb_status = "중심선 위 (상승 압력)"
                else:
                    bb_status = "중심선 아래 (하락 압력)"

                reasoning_lines.append(f"볼린저밴드: {bb_status}")
            reasoning_lines.append("")

        # 2. Bull의 의견 (간략)
        if bull and isinstance(bull, dict):
            bull_rationale = bull.get("rationale", "")
            if bull_rationale:
                reasoning_lines.append("【Bull (강세론)】")
                reasoning_lines.append(f"{bull_rationale}")
                reasoning_lines.append("")

        # 3. Bear의 의견 (간략)
        if bear and isinstance(bear, dict):
            bear_rationale = bear.get("rationale", "")
            if bear_rationale:
                reasoning_lines.append("【Bear (약세론)】")
                reasoning_lines.append(f"{bear_rationale}")
                reasoning_lines.append("")

        # 4. Trader의 제안
        reasoning_lines.append("【Trader 제안】")
        if trader_rationale:
            reasoning_lines.append(f"{action} - {trader_rationale}")
        else:
            reasoning_lines.append(f"{action} 제안")
        if confidence:
            reasoning_lines.append(f"확신도: {confidence}")
        reasoning_lines.append("")

        # 5. Manager의 최종 결정
        reasoning_lines.append("【Manager 최종 결정】")

        # Manager의 rationale 우선 확인 (가장 직접적인 이유)
        manager_rationale = report.get("rationale", "")

        # Manager가 여러 옵션을 제시했는지 확인
        original_manager_strategy = report.get("strategy", "")
        has_multiple_options = "|" in original_manager_strategy if original_manager_strategy else False

        if manager_strategy and manager_strategy != action:
            # Manager가 Trader 제안을 수정한 경우
            if has_multiple_options:
                # 여러 옵션 중 선택한 경우
                reasoning_lines.append(f"최종 결정: {manager_strategy} (후보: {original_manager_strategy})")
            else:
                reasoning_lines.append(f"최종 결정: {manager_strategy}")
            reasoning_lines.append(f"Trader의 {action} 제안을 {manager_strategy}로 수정")

            # 1차: report.rationale에서 Manager의 직접적인 이유 확인
            if manager_rationale:
                reasoning_lines.append(f"결정 이유: {manager_rationale}")
            else:
                # 2차: reflection에서 Manager의 판단 근거 추출
                reflection_text = reflection_data.get("reflection", "") if reflection_data else ""

                reason_found = False
                if reflection_text:
                    # "Backtest feedback" 이후 제거
                    if "Backtest feedback" in reflection_text:
                        reflection_text = reflection_text.split("Backtest feedback")[0].strip()

                    # "그러나", "하지만" 등 Manager의 반대 의견 찾기
                    contradiction_markers = ["그러나", "하지만", "다만", "반면"]
                    reason_text = ""

                    for marker in contradiction_markers:
                        if marker in reflection_text:
                            # 해당 마커 이후 텍스트 추출
                            parts = reflection_text.split(marker, 1)
                            if len(parts) > 1:
                                after_marker = parts[1].strip()
                                # "Manager는 XXX 전략으로 결정" 패턴 찾기
                                if "전략으로 결정" in after_marker:
                                    # 그 앞부분이 이유
                                    before_decision = parts[0].strip()
                                    # Bull/Bear의 의견을 요약
                                    if "Bull" in before_decision or "Bear" in before_decision:
                                        reason_text = f"Bull과 Bear의 의견을 검토한 결과, "

                                    # "전략으로 결정" 앞의 내용 추가
                                    decision_parts = after_marker.split("전략으로 결정")[0]
                                    if decision_parts:
                                        reason_text += decision_parts.strip()
                                        reason_found = True
                                        break

                    # 패턴을 못 찾으면 전체 reflection 정리해서 사용
                    if not reason_found and reflection_text:
                        # "Manager는" 이후 내용만
                        if "Manager는" in reflection_text:
                            manager_part = reflection_text[reflection_text.find("Manager는"):]
                            # 첫 2문장만
                            sentences = [s.strip() for s in manager_part.split(".") if s.strip()]
                            clean_sentences = []
                            for s in sentences[:2]:
                                if "final_equity" not in s and "total_return" not in s and "Backtest" not in s:
                                    clean_sentences.append(s)
                            if clean_sentences:
                                reason_text = ". ".join(clean_sentences) + "."
                                reason_found = True

                    if reason_found and reason_text:
                        reasoning_lines.append(f"결정 이유: {reason_text}")

                # 3차: 이유를 못 찾으면 Bull/Bear 의견과 비교
                if not reason_found:
                    # Bull이 긍정적이고 Bear가 부정적인데 SELL을 선택했다면
                    bull_action = bull.get("action", "") if isinstance(bull, dict) else ""
                    bear_action = bear.get("action", "") if isinstance(bear, dict) else ""

                    if "SELL" in manager_strategy:
                        if "BUY" in action:
                            reasoning_lines.append(f"결정 이유: Bear의 하락 전망과 리스크 요소를 더 신뢰하여 보수적 전략 선택")
                        else:
                            reasoning_lines.append(f"결정 이유: 시장 리스크를 고려하여 보수적으로 접근")
                    elif "BUY" in manager_strategy:
                        if "SELL" in action:
                            reasoning_lines.append(f"결정 이유: Bull의 상승 전망을 신뢰하여 적극적 전략 선택")
                        else:
                            reasoning_lines.append(f"결정 이유: 상승 모멘텀을 포착하여 매수 결정")
                    elif "HOLD" in manager_strategy:
                        reasoning_lines.append(f"결정 이유: 시장 불확실성으로 인해 관망 전략 선택")
                    else:
                        reasoning_lines.append(f"결정 이유: 종합적인 시장 분석 결과에 따라 전략 조정")
        else:
            # Trader와 Manager가 일치
            if has_multiple_options:
                reasoning_lines.append(f"최종 결정: {final_action} (후보: {original_manager_strategy})")
            else:
                reasoning_lines.append(f"최종 결정: {final_action}")

            if manager_rationale:
                reasoning_lines.append(f"승인 이유: {manager_rationale}")
            elif manager_strategy:
                if has_multiple_options:
                    reasoning_lines.append(f"승인 이유: 여러 옵션 중 {final_action}을 최적으로 판단")
                else:
                    reasoning_lines.append(f"승인 이유: Trader의 분석이 타당하다고 판단")
            else:
                reasoning_lines.append(f"승인 이유: Trader의 제안을 그대로 수용")

        # 6. 리스크 및 주의사항
        risks = report.get("risks", [])
        if risks:
            reasoning_lines.append("")
            reasoning_lines.append("【주의사항】")
            for risk in risks:
                if risk and not risk.startswith("리스크"):
                    reasoning_lines.append(f"⚠️ {risk}")

        # 7. 과거 학습 패턴 (메모리 사용 시)
        long_term_mem = summary.get("memories", {}).get("long_term", [])
        if use_memory and long_term_mem:
            reasoning_lines.append("")
            reasoning_lines.append("【과거 학습 데이터】")
            try:
                import json
                for idx, mem in enumerate(long_term_mem[:2], 1):  # 최대 2개
                    mem_content_str = mem.get("content", "{}")
                    try:
                        mem_content = json.loads(mem_content_str)
                        next_steps = mem_content.get("next_steps", [])
                        if next_steps:
                            # 평균 수익률 계산
                            returns = []
                            for step in next_steps[:3]:
                                if "total_return=" in step:
                                    return_val = float(step.split("total_return=")[1].strip().rstrip(")"))
                                    returns.append(return_val * 100)
                            if returns:
                                avg_return = sum(returns) / len(returns)
                                reasoning_lines.append(f"💡 유사 패턴 #{idx}: 평균 수익률 {avg_return:+.2f}%")
                    except:
                        pass
            except:
                pass

        reasoning = "\n".join(reasoning_lines) if reasoning_lines else "AI 에이전트가 시장 데이터를 분석하여 결정했습니다."

        print("\n" + "=" * 80)
        print("📊 거래 추천 결과")
        print("=" * 80)

        # 액션 출력 (최종 결정 사용)
        action_display = final_action.upper()
        if "BUY" in action_display:
            action_percent = "25%" if "25" in action_display else "50%" if "50" in action_display else "100%" if "100" in action_display else ""
            print(f"🟢 추천 액션: {action_display} (매수 {action_percent})")
        elif "SELL" in action_display:
            action_percent = "25%" if "25" in action_display else "50%" if "50" in action_display else "100%" if "100" in action_display else ""
            print(f"🔴 추천 액션: {action_display} (매도 {action_percent})")
        else:
            print(f"⚪ 추천 액션: {action_display} (홀드)")

        print(f"\n📝 추천 근거:")
        # 줄바꿈 처리
        for line in reasoning.split('\n'):
            if line.strip():
                print(f"  {line.strip()}")

        # 시장 데이터 표시
        latest = summary.get("latest", {})
        if latest:
            print(f"\n📈 현재 시장 데이터:")
            print(f"  종가: ${latest.get('close', 0):.2f}")
            print(f"  고가: ${latest.get('high', 0):.2f}")
            print(f"  저가: ${latest.get('low', 0):.2f}")
            print(f"  거래량: {latest.get('volume', 0):,.0f}")

            # 기술적 지표
            if 'rsi' in latest:
                print(f"\n📊 기술적 지표:")
                print(f"  RSI: {latest.get('rsi', 0):.2f}")
                print(f"  볼린저 상단: ${latest.get('bb_upper', 0):.2f}")
                print(f"  볼린저 중간: ${latest.get('bb_middle', 0):.2f}")
                print(f"  볼린저 하단: ${latest.get('bb_lower', 0):.2f}")

        # 메모리 정보 표시
        memories = summary.get("memories", {})
        if use_memory and memories:
            long_term = memories.get("long_term", [])
            working = memories.get("working", [])
            print(f"\n🧠 사용된 메모리:")
            print(f"  장기 메모리: {len(long_term)}개")
            print(f"  작업 메모리: {len(working)}개")

        print("\n" + "=" * 80)
        print(f"✓ 분석 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
