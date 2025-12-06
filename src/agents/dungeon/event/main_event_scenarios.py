import os
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


MAIN_EVENT_SCENARIOS = [
    {
        "event_id": 1,
        "event_code": "BLACK_FIGURE",
        "title": "검은 형상의 무언가",
        "is_personal": False,
        "scenario_text": (
            "방의 한 가운데에 검은 형상을 한 무언가가 존재한다. "
            "그것은 빛을 집어삼키듯 어둡고, 주변의 공기마저 무겁게 짓누르고 있다."
        ),
    },
    {
        "event_id": 2,
        "event_code": "COLLAPSED_PERSON",
        "title": "쓰러져있는 사람",
        "is_personal": False,
        "scenario_text": (
            "방의 구석에 웅크린 채 누워있는 사람이 보인다. "
            "낡은 후드를 뒤집어쓰고 있어 종족이나 성별, 나이를 가늠하기 힘들다. "
            "미세한 숨소리만이 그가 살아있음을 알리고 있다."
        ),
    },
    {
        "event_id": 3,
        "event_code": "ALTAR_WATER",
        "title": "제단속에 고여있는 물",
        "is_personal": False,
        "scenario_text": (
            "방의 한 가운데에 가슴 높이까지 오는 작은 사각형 기둥이 놓여 있다. "
            "기둥의 가운데는 깊게 파여 있으며, 그 안에는 맑은 물이 찰랑거리고 있다. "
            "수면 위로 은은한 빛이 감돌고 있다."
        ),
    },
    {
        "event_id": 4,
        "event_code": "MAD_MERCHANT",
        "title": "미치광이 상인",
        "is_personal": False,
        "scenario_text": (
            "방의 한 가운데에 낡은 후드를 쓴 사람이 서 있다. "
            "자신을 상인이라고 소개한 그는, 기괴한 웃음을 멈추지 못하며 이쪽을 뚫어지게 응시한다. "
            "그의 눈빛에는 광기와 탐욕이 뒤섞여 있다."
        ),
    },
    {
        "event_id": 5,
        "event_code": "UNKNOWN_MEMORY",
        "title": "미지의 기억",
        "is_personal": False,
        "scenario_text": (
            "방에 들어서는 순간, 시야가 흐릿해지며 낯선 풍경이 눈앞에 펼쳐진다. "
            "이전에 경험해보지 못한 상황, 낯선 감각들이 전신을 휘감는다. "
            "이곳은 현실이 아닌, 누군가의 기억 속인 듯하다."
        ),
    },
    {
        "event_id": 6,
        "event_code": "CRUSHING_GUILT",
        "title": "조여오는 죄책감",
        "is_personal": True,
        "scenario_text": (
            "방에 입장하는 순간, {heroine_name}의 머릿속을 날카로운 기억이 헤집는다. "
            "잊고 싶었던 트라우마가 되살아나며, 정신을 족쇄처럼 옭아맨다. "
            "마음 깊은 곳에서부터 죄책감이 서서히 차오른다."
        ),
    },
    {
        "event_id": 7,
        "event_code": "EXIT_8",
        "title": "8번 출구",
        "is_personal": False,
        "scenario_text": (
            "방에 입장했으나 별다른 인기척은 느껴지지 않는다. "
            "다만, 방의 어딘가에 원래는 없어야 할 이질적인 물건이 놓여 있다. "
            "평범해 보이는 풍경 속에 숨겨진 위화감이 감돈다."
        ),
    },
    {
        "event_id": 8,
        "event_code": "ABYSS_WORSHIPPER",
        "title": "심연을 숭배하는 자",
        "is_personal": False,
        "scenario_text": (
            "방 한가운데에 후드를 깊게 눌러쓴 인물이 서 있다. "
            "그는 무언가를 중얼거리고 있으나, 심하게 더듬거려 알아듣기 힘들다. "
            "이해할 수 없는 단어들이 공허하게 울려 퍼진다."
        ),
    },
    {
        "event_id": 9,
        "event_code": "CONDITION_ROOM",
        "title": "XX 해야 탈출할 수 있는 방",
        "is_personal": False,
        "scenario_text": (
            "방 중앙에 낡은 표지판이 하나 세워져 있다. "
            "표지판에는 이곳을 나가기 위해 수행해야 할 특정한 행동이 적혀 있다. "
            "방의 문은 굳게 닫혀 있어, 지시를 따르지 않고는 나갈 수 없어 보인다."
        ),
    },
    {
        "event_id": 10,
        "event_code": "IRRESISTIBLE_TEMPTATION",
        "title": "떨쳐내기 힘든 유혹",
        "is_personal": True,
        "scenario_text": (
            "방에 입장하자 시야가 검게 흐려진다. "
            "눈앞에는, {heroine_name}가 평소 갈망하던 것들이 아른거린다. "
            "달콤한 향기와 함께, 그쪽으로 다가가길 유도하는 듯한 속삭임이 들려온다."
        ),
    },
]
