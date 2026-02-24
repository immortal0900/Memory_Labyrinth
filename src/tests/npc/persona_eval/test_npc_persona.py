"""
NPC 페르소나 평가 테스트

DeepEval을 사용하여 NPC의 페르소나 일관성, 역할 몰입도, 지식 경계를 평가합니다.

[2-Phase Memory Gap 설계]
multi_turn_memory 테스트는 정보 제공(Phase 1)과 기억 확인(Phase 2) 사이에
다른 유형의 질문을 MEMORY_GAP_TURNS개 끼워넣어 장기 기억을 테스트합니다.

  Phase 1: 정보 제공 턴 전송 ("나는 민수야")
     ↓
  Gap:     다른 유형 질문 4개 실행 (conversation_buffer 밀어내기)
     ↓
  Phase 2: 기억 확인 턴 전송 ("내 이름 뭐라고 했지?")

이렇게 하면 프롬프트의 최근 대화 5턴(conversation_buffer)에서
정보 제공 턴이 밀려나가므로, DB 기반 장기 기억 검색 능력을 평가할 수 있습니다.
"""

import pytest
from .custom_metrics import (
    get_metrics_for_type,
    calculate_weighted_score,
    get_primary_metric
)
from deepeval.test_case import LLMTestCase
from .npc_client import NPCClient
from typing import List, Dict, Any, Tuple, Callable, Awaitable

# --------------------------------------------------------------------------- #
# 전역 설정
# --------------------------------------------------------------------------- #

# 전역 결과 저장소 (마지막에 종합 리포트를 출력하기 위함)
GLOBAL_RESULTS = []

# 정보 제공 턴과 기억 확인 턴 사이에 끼워넣을 다른 대화 턴 수
# NPC 프롬프트의 conversation_buffer가 최근 5턴을 포함하므로,
# 5턴을 사이에 넣어야 정보 제공 턴이 buffer 밖으로 완전히 밀려남.
# (4턴만 넣으면 정보 제공 턴이 5턴 window의 첫 번째에 걸림)
# 이 값이 없을 경우: 정보 제공 직후 기억 확인이 되어 단기 기억만 테스트됨.
MEMORY_GAP_TURNS = 5


# --------------------------------------------------------------------------- #
# pytest 세션 fixture
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session", autouse=True)
def summary_report_fixture():
    """모든 테스트 세션이 끝나면 종합 리포트를 출력합니다."""
    yield
    print_final_summary()


# --------------------------------------------------------------------------- #
# 2-Phase Memory Gap 핵심 로직
# --------------------------------------------------------------------------- #

async def _build_test_cases_with_memory_gap(
    questions: List[Dict[str, Any]],
    chat_func: Callable[[str], Awaitable[Dict[str, Any]]],
    persona_context: str,
) -> Dict[str, List[Tuple[LLMTestCase, Dict[str, Any]]]]:
    """
    multi_turn_memory 질문을 2-Phase로 분리하여 장기 기억을 테스트합니다.

    [데이터 흐름]
    1. 전체 질문을 memory / non-memory로 분류
    2. memory 질문의 Phase 1(정보 제공 턴)을 먼저 전송
    3. non-memory 질문 중 MEMORY_GAP_TURNS개를 사이에 실행 (buffer 밀어내기)
    4. memory 질문의 Phase 2(기억 확인 턴)를 전송 → 장기 기억 검증
    5. 남은 non-memory 질문을 순차 실행

    [이것이 없을 경우 발생할 문제]
    모든 질문이 유형별로 순차 실행되어 multi_turn_memory의
    turns[0]→turns[1]이 연속 호출됨 → 단기 기억만 테스트됨.

    Args:
        questions: 캐릭터 질문 데이터셋 리스트
        chat_func: NPC와 대화하는 비동기 함수 (메시지 -> 응답)
        persona_context: 채점 기준에 사용할 페르소나 정의 문자열

    Returns:
        유형별 (LLMTestCase, question_info) 튜플 리스트 딕셔너리
    """

    # --- 1단계: 질문 분류 ---
    memory_questions = [q for q in questions if q["type"] == "multi_turn_memory"]
    other_questions = [q for q in questions if q["type"] != "multi_turn_memory"]

    test_cases_by_type: Dict[str, List[Tuple[LLMTestCase, Dict[str, Any]]]] = {}

    def _append_test_case(q_info: Dict, test_case: LLMTestCase) -> None:
        """유형별 딕셔너리에 (시험지, 상세정보) 세트를 추가하는 헬퍼."""
        q_type = q_info["type"]
        if q_type not in test_cases_by_type:
            test_cases_by_type[q_type] = []
        test_cases_by_type[q_type].append((test_case, q_info))

    # --- 2단계: Phase 1 — memory 질문의 정보 제공 턴 전송 ---
    for mq in memory_questions:
        turns = mq["turns"]
        print(f"    [Memory Phase 1] 정보 제공: \"{turns[0]['content']}\"")
        await chat_func(turns[0]["content"])

    # --- 3단계: Gap — 다른 유형 질문으로 conversation_buffer 밀어내기 ---
    # 질문별 memory_gap 값이 있으면 해당 값 사용, 없으면 전역 상수 사용
    gap_size = MEMORY_GAP_TURNS
    if memory_questions:
        gap_size = memory_questions[0].get("memory_gap", MEMORY_GAP_TURNS)

    gap_questions = other_questions[:gap_size]
    remaining_questions = other_questions[gap_size:]

    print(f"    [Memory Gap] {len(gap_questions)}턴의 다른 질문 실행 중...")

    for q_info in gap_questions:
        response = await chat_func(q_info["turns"][0]["content"])
        test_case = LLMTestCase(
            input=q_info["turns"][0]["content"],
            actual_output=response["text"],
            context=[persona_context, f"올바른 응답 방향: {q_info['expected_behavior']}"]
        )
        _append_test_case(q_info, test_case)

    # --- 4단계: Phase 2 — memory 질문의 기억 확인 턴 전송 ---
    for mq in memory_questions:
        turns = mq["turns"]
        print(f"    [Memory Phase 2] 기억 확인: \"{turns[1]['content']}\"")
        response = await chat_func(turns[1]["content"])
        test_case = LLMTestCase(
            input=f"{turns[0]['content']} -> {turns[1]['content']}",
            actual_output=response["text"],
            context=[persona_context, f"올바른 응답 방향: {mq['expected_behavior']}"]
        )
        _append_test_case(mq, test_case)

    # --- 5단계: 나머지 질문 순차 실행 ---
    for q_info in remaining_questions:
        response = await chat_func(q_info["turns"][0]["content"])
        test_case = LLMTestCase(
            input=q_info["turns"][0]["content"],
            actual_output=response["text"],
            context=[persona_context, f"올바른 응답 방향: {q_info['expected_behavior']}"]
        )
        _append_test_case(q_info, test_case)

    return test_cases_by_type


# --------------------------------------------------------------------------- #
# 평가 실행 및 리포트
# --------------------------------------------------------------------------- #

def run_evaluation_by_type(test_cases_by_type, character_name):
    """
    유형별로 테스트를 실행하고 가중 점수를 계산하여 결과를 수집합니다.

    [입력 데이터 구조 예시]
    test_cases_by_type = {
        "memory": [
            (test_case1, question_info1),
            (test_case2, question_info2)
        ]


    1. test_case (LLMTestCase): 채점관(DeepEval)을 위한 '기술적 시험지'
       - input: "아이폰 써봤어?" (질문 텍스트)
       - actual_output: "아이폰? 그게 무엇인지 모르겠군요." (AI의 실제 답변)
       - context: ["성격...", "지침..."] (채점 기준들)

    2. question_info (dict): 개발자를 위한 '질문 상세 정보 주머니'
       - id: "letia_005" (관리용 번호)
       - type: "knowledge_boundary" (질문 유형)
       - turns: [{"role": "user", "content": "..."}] (질문 원본)
       - persona_context: "테스트 의도"
       - expected_behavior: "채점 가이드라인"

    """
    character_summary = {
        "character": character_name,
        "results": []
    }

    for question_type, case_list in test_cases_by_type.items():
        if not case_list:
            continue

        metrics = get_metrics_for_type(question_type)
        primary_metric_name = get_primary_metric(question_type)

        print(f"\n>>> [{character_name}] '{question_type}' 유형 평가 시작 ({len(case_list)}개)")

        type_scores = []
        for test_case, q_info in case_list:
            metric_scores = {}

            # 개별 채점(measure) 수행
            for metric in metrics:
                metric.measure(test_case)
                metric_scores[metric.name] = metric.score if metric.score else 0.0

            weighted_score = calculate_weighted_score(question_type, metric_scores)
            type_scores.append(weighted_score)

            # 개별 질문 결과 즉시 출력
            print(f"  * [{q_info['id']}] {q_info['persona_context']}")
            print(f"    - 질문: {test_case.input}")
            print(f"    - 답변: {test_case.actual_output}")
            print(f"    - 가중 점수: {weighted_score:.2%}")
            # 주요 메트릭의 이유(Reason) 출력
            for metric in metrics:
                if metric.name == primary_metric_name:
                    print(f"    - 판단 이유: {metric.reason}")

        if type_scores:
            type_avg = sum(type_scores) / len(type_scores)
            character_summary["results"].append({
                "type": question_type,
                "score": type_avg,
                "count": len(type_scores)
            })

    GLOBAL_RESULTS.append(character_summary)

def print_final_summary():
    """모든 캐릭터의 테스트 결과를 깔끔하게 정리하여 출력합니다."""
    print("\n\n" + "="*60)
    print("             [ NPC 페르소나 평가 종합 리포트 ]")
    print("="*60)

    total_score_sum = 0
    total_test_count = 0

    # 캐릭터 이름순 정렬 (출력 순서 고정)
    sorted_results = sorted(GLOBAL_RESULTS, key=lambda x: x['character'])

    for char_data in sorted_results:
        print(f"\n● 캐릭터: {char_data['character']}")
        char_score_sum = 0
        char_test_count = 0

        # 유형별 결과 출력
        for res in char_data["results"]:
            print(f"  - {res['type']:<20} | 평균 {res['score']:>7.2%} ({res['count']}개 질문)")
            char_score_sum += res['score'] * res['count']
            char_test_count += res['count']

        if char_test_count > 0:
            char_avg = char_score_sum / char_test_count
            print(f"  [ {char_data['character']} 합계 점수: {char_avg:.2%} ]")
            total_score_sum += char_score_sum
            total_test_count += char_test_count

    print("\n" + "="*60)
    if total_test_count > 0:
        total_avg = total_score_sum / total_test_count
        print(f"■ 최종 결과: 총 {total_test_count}개 질문 평가 완료 / 전체 평균 점수 {total_avg:.2%}")
    else:
        print("평가 데이터가 없습니다.")
    print("="*60 + "\n")


# ============================================
# 캐릭터별 테스트 함수 (데이터 조립소)
# ============================================

@pytest.mark.asyncio
async def test_letia_persona(npc_client, letia_questions, letia_persona):
    """레티아 페르소나 평가 테스트"""
    player_id = "test_letia_player"
    heroine_id = 1
    await npc_client.login(player_id)

    # chat_func: 메시지만 넣으면 해당 히로인에게 전송하는 클로저
    async def chat_func(message: str) -> Dict[str, Any]:
        return await npc_client.chat_heroine(player_id, heroine_id, message)

    test_cases_by_type = await _build_test_cases_with_memory_gap(
        questions=letia_questions,
        chat_func=chat_func,
        persona_context=letia_persona,
    )

    run_evaluation_by_type(test_cases_by_type, "레티아")

@pytest.mark.asyncio
async def test_lupames_persona(npc_client, lupames_questions, lupames_persona):
    """루파메스 페르소나 평가 테스트"""
    player_id = "test_lupames_player"
    heroine_id = 2
    await npc_client.login(player_id)

    async def chat_func(message: str) -> Dict[str, Any]:
        return await npc_client.chat_heroine(player_id, heroine_id, message)

    test_cases_by_type = await _build_test_cases_with_memory_gap(
        questions=lupames_questions,
        chat_func=chat_func,
        persona_context=lupames_persona,
    )

    run_evaluation_by_type(test_cases_by_type, "루파메스")


@pytest.mark.asyncio
async def test_roco_persona(npc_client, roco_questions, roco_persona):
    """로코 페르소나 평가 테스트"""
    player_id = "test_roco_player"
    heroine_id = 3
    await npc_client.login(player_id)

    async def chat_func(message: str) -> Dict[str, Any]:
        return await npc_client.chat_heroine(player_id, heroine_id, message)

    test_cases_by_type = await _build_test_cases_with_memory_gap(
        questions=roco_questions,
        chat_func=chat_func,
        persona_context=roco_persona,
    )

    run_evaluation_by_type(test_cases_by_type, "로코")


@pytest.mark.asyncio
async def test_satra_persona(npc_client, satra_questions, satra_persona):
    """사트라 페르소나 평가 테스트"""
    player_id = "test_satra_player"
    await npc_client.login(player_id, scenario_level=1)

    async def chat_func(message: str) -> Dict[str, Any]:
        return await npc_client.chat_sage(player_id, message)

    test_cases_by_type = await _build_test_cases_with_memory_gap(
        questions=satra_questions,
        chat_func=chat_func,
        persona_context=satra_persona,
    )

    run_evaluation_by_type(test_cases_by_type, "사트라")
