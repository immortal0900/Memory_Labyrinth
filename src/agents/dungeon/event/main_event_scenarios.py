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
            "당신은 방에 입장하는 순간부터 그 무언가를 인지하며, 이벤트가 시작된다."
        ),
    },
    {
        "event_id": 2,
        "event_code": "COLLAPSED_PERSON",
        "title": "쓰러져있는 사람",
        "is_personal": False,
        "scenario_text": (
            "방의 구석에 웅크린 채 누워있는 사람이 보인다. "
            "후드를 뒤집어 쓰고 있기에 종족이나 성별, 나이를 가늠하기 힘들다."
        ),
    },
    {
        "event_id": 3,
        "event_code": "ALTAR_WATER",
        "title": "제단속에 고여있는 물",
        "is_personal": False,
        "scenario_text": (
            "방의 한 가운데에 당신의 가슴 높이까지 오는 작은 사각형 기둥이 있다. "
            "가운데는 깊게 파여 있으며, 그 안에 물이 고여있다."
        ),
    },
    {
        "event_id": 4,
        "event_code": "MAD_MERCHANT",
        "title": "미치광이 상인",
        "is_personal": False,
        "scenario_text": (
            "방의 한 가운데에 낡은 후드를 쓴 사람이 서있다. "
            "자신을 상인이라고 소개한 그 사람은, 웃음을 멈추지 못하며 당신을 계속 응시한다. "
            "상인에게 관심을 가지고 말을 건다면, 그는 특별한 기억을 판매하겠다며 "
            "대신 당신의 기억을 달라고 요청한다."
        ),
    },
    {
        "event_id": 5,
        "event_code": "UNKNOWN_MEMORY",
        "title": "미지의 기억",
        "is_personal": False,
        "scenario_text": (
            "방에 들어가는 순간, 당신은 갑자기 머리속이 흐릿해지며 "
            "이전에 경험해보지 못한 상황이 눈앞에 펼쳐진다. "
            "머리속에서 펼쳐지는 미지의 기억 속에서, 당신은 어떻게 행동할 것인지 결정해야 한다. "
            "중요한 것은 그 기억 속에서 탈출해 정신을 차리는 것이다."
        ),
    },
    {
        "event_id": 6,
        "event_code": "CRUSHING_GUILT",
        "title": "조여오는 죄책감",
        "is_personal": True,
        "scenario_text": (
            "방에 입장하는 순간, 당신의 머리속을 어떤 기억이 헤집는다. "
            "당신의 트라우마와 관련이 있는 그 기억은, "
            "당신의 정신에 족쇄처럼 얽매이며 마음을 서서히 갉아먹는다. "
            "상황에 적절히 대응하여, 당신의 트라우마를 극복해야 한다."
        ),
    },
    {
        "event_id": 7,
        "event_code": "EXIT_8",
        "title": "8번 출구",
        "is_personal": False,
        "scenario_text": (
            "방에 입장해도 별다른 반응이 없다. "
            "방의 랜덤한 한 곳에, 원래는 없어야 할 물건이 뜬금없이 생성되어 있다. "
            "그것이 무엇이든 상관없다. 중요한 것은 그것을 눈치챘는가 하는 점이다."
        ),
    },
    {
        "event_id": 8,
        "event_code": "ABYSS_WORSHIPPER",
        "title": "심연을 숭배하는 자",
        "is_personal": False,
        "scenario_text": (
            "방 한가운데에 후드를 쓴 인물이 등장한다. "
            "인물에게 말을 걸면 엄청 더듬으며, 전혀 이해할 수 없는 이상한 말만 내뱉는다."
        ),
    },
    {
        "event_id": 9,
        "event_code": "CONDITION_ROOM",
        "title": "XX 해야 탈출할 수 있는 방",
        "is_personal": False,
        "scenario_text": (
            "방 중앙에 글이 써있는 표지판이 세워져 있다. "
            "그 표지판에는 당신에게 특정한 행동을 유도하는 글이 쓰여 있다."
        ),
    },
    {
        "event_id": 10,
        "event_code": "IRRESISTIBLE_TEMPTATION",
        "title": "떨쳐내기 힘든 유혹",
        "is_personal": True,
        "scenario_text": (
            "방에 입장하면 화면이 검은색으로 채워진다. "
            "당신의 눈앞에는, 당신이 좋아하는 것들이 등장하며 "
            "당신을 그쪽으로 다가가도록 유도한다."
        ),
    },
]
