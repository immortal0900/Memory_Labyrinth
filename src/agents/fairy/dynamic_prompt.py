dungeon_spec_prompt = """
아래는 현재 플레이어가 탐험 중인 던전의 전체 구조를 설명하는 데이터입니다.
던전은 방(room), 몬스터 스폰 정보, 보상 테이블 등으로 구성되며,
각 필드의 의미와 값의 범위는 다음 스펙을 참고하면 됩니다.

이 정보는 현재 위치한 방의 형태, 연결된 경로, 등장 가능한 몬스터,
획득 가능한 보상 등을 이해하는 데 사용됩니다.

■ playerIds (int[])
  - 던전에 참여한 플레이어 ID 목록

■ heroineIds (int[])
  - 각 플레이어가 선택한 히로인 ID 목록

■ rooms (roomData[])
  던전을 구성하는 방 목록입니다.

  ● roomId (int)
      각 방의 고유 ID

  ● type (int)
      방의 종류  
        0: 빈 방  
        1: 전투 방  
        2: 이벤트 방  
        3: 보물 방

  ● size (int)
      방의 크기 (2~4)

  ● neighbors (int[])
      이 방과 연결된 roomId 목록

  ● monsters (monsterSpawnData[] | null)
      전투 방일 경우 등장하는 몬스터 목록  
      monsterSpawnData 구조는 아래와 같습니다:
        - monsterId (int)
        - posX (float, 0~1)
        - posY (float, 0~1)

  ● eventType (int | null)
      이벤트 방일 경우 이벤트 종류 ID

■ rewards (rewardTable[])
  던전에서 등장 가능한 보상 목록입니다.
  rewardTable 구조는 다음과 같습니다:
    - rarity (int, 0~3)
    - itemTable (int[])

아래 JSON은 실제 현재 던전의 전체 데이터입니다.

{balanced_map_json}
"""

item_spec_prompt = """
아래는 플레이어가 보유/획득/장착할 수 있는 아이템(Item)과,
무기(Weapon) 상세 정보를 설명하는 데이터 스펙입니다.

아이템은 공통 필드(이름/ID/타입/등급)를 가지며,
무기 타입 아이템인 경우 weapon 필드에 무기 스탯 정보가 포함됩니다.

■ items (ItemData[])
  아이템 목록입니다. (예: 인벤토리, 드랍 보상, 상점 목록 등)

  ● itemId (int)
      아이템 고유 ID

  ● itemName (string | null)
      아이템 이름 (없을 수 있음)

  ● itemType (int)
      아이템 타입
        0: 장신구
        1: 한손검
        2: 쌍검
        3: 대검
        4: 둔기(두손둔기)

  ● rarity (int, 0~3)
      아이템 등급
        0: 커먼
        1: 언커먼
        2: 레어
        3: 레전드

  ● weapon (WeaponData | null)
      무기 타입 아이템일 때만 존재하며, 무기 스탯/보정치 정보입니다.
      (장신구 등 무기가 아닌 아이템이면 null)

------------------------------------------------------------

■ WeaponData
  무기 상세 정보 구조는 다음과 같습니다.

  ● weaponId (int | null)
      무기 고유 ID (없을 수 있음)

  ● weaponType (int)
      무기 타입
        0: 한손검
        1: 쌍검
        2: 대검
        3: 둔기

  ● weaponName (string | null)
      무기 이름 (없을 수 있음)

  ● rarity (int, 0~3)
      무기 등급 (아이템 등급과 동일)

  ● attackPower (int)
      무기 기본 공격력

  ● staggerPower (int | null)
      무기 그로기 공격력 (없을 수 있음)

  ● modifier (object<string, float>)
      스탯별 보정치 맵
      - key: 스탯 이름 문자열 (예: "strength", "dexterity")
      - value: 보정치(float)
      예: {{ "strength": 0.5, "dexterity": 0.5, "intelligence":0 }}

아래 JSON은 실제 아이템 데이터입니다.

{items_json}
"""

monster_spec_prompt = """
아래는 던전에서 등장 가능한 몬스터의 기본 스펙 정보를 설명하는 데이터입니다.
이 정보는 몬스터의 체력/이동/공격/사거리/그로기 수치, 경험치(exp),
그리고 약점/강점 텍스트를 이해하는 데 사용됩니다.

※ mesh 경로 필드는 이 데이터에서는 제외되어 있습니다.

■ monsters (MonsterInfo[])
  몬스터 목록입니다.

  ● monsterId (int)
      몬스터 고유 ID

  ● monsterType (int)
      몬스터 분류 타입 ID
      - 현재 데이터 기준으로는 아래처럼 사용되고 있습니다:
        0: 일반 몬스터
        1: 언데드 계열
        2: 보스 계열

  ● monsterName (string)
      몬스터 이름

  ● hp (int)
      몬스터 체력

  ● speed (int)
      몬스터 이동 속도

  ● attack (int)
      몬스터 기본 공격력

  ● attackSpeed (float)
      몬스터 공격 속도 배율
      - 예: 1.0(기본), 0.7(느림), 1.5(빠름)

  ● attackRange (int)
      몬스터 공격 사거리

  ● staggerGage (int)
      몬스터 그로기(스태거) 게이지/내성 수치
      - 값이 클수록 그로기 유발이 어려운 형태로 해석 가능
      (※ 실제 로직은 게임 규칙에 따름)

  ● exp (int)
      몬스터 처치 시 획득 경험치

  ● weaknesses (string | null)
      몬스터 약점(설명 텍스트)
      - 없으면 null
      - 해당 공격에 몬스터가 약하다.
      - 예: "넉백, 타격"

  ● strengths (string | null)
      몬스터 강점(설명 텍스트)
      - 없으면 null
      - 해당 공격에 몬스터가 강하다. (해당 스킬을 몬스터가 쓰면 쎄다가 아님)
      - 예: "강한 한방"

아래 JSON은 실제 몬스터 스펙 데이터입니다.

{monster_infos_json}
"""




# fairy_examples.py 같은 파일로 분리 추천
from agents.fairy.fairy_state import FairyDungeonIntentType
FAIRY_DUNGEON_FEW_SHOTS: dict[FairyDungeonIntentType, str] = {
FairyDungeonIntentType.USAGE_GUIDE: """
[예시 1 – 사용자가 시스템 관련 질문을 할 때]
- (가정 상황)
  - 사용자가 스킬 사용 방법 같은 시스템/조작 관련 질문을 하고 있다고 가정한다.

- (나쁜 예시)
  - (능력: USAGE_GUIDE)
  - User: 스킬은 어떻게 써?
  - Paimon: 그냥 E 눌러!
  # → 정보가 너무 적고, R 같은 연관된 키 설명이 빠져 있음.

- (좋은 예시)
  - (능력: USAGE_GUIDE)
  - User: 스킬은 어떻게 써?
  - Paimon: 스킬은 E랑 R 키로 쓸 수 있어! E는 무기 스킬이고, R은 네 직업 스킬이야!

- → 핵심 포인트
  - 질문에 “스킬”이 포함되어 있다면, 관련된 모든 정보를 빠짐없이 제공해야 한다.
  - 조작/시스템 질문일 경우, 연결된 키나 기능을 최대한 함께 설명한다.


[예시 2 – 시스템 규칙을 설명할 때는 현재 위치와 동행 중인 히로인을 고려한다]

- (가정 상황 1)
  - 플레이어는 현재 던전 안에 있다.
  - 동행 중인 히로인: 로코.
  - 이 세계관에서 플레이어는 로코의 멘토다.

- (나쁜 예시 1)
  - (능력: USAGE_GUIDE)
  - User: 메모리 샤드를 얻은 다음엔 뭐 해야 해?
  - Paimon: 그냥 히로인 만나러 가!
  # → 로코의 이름이 없고, 아직 던전 안이라는 상황을 무시함.

- (좋은 예시 1)
  - (능력: USAGE_GUIDE)
  - User: 메모리 샤드를 얻은 다음엔 뭐 해야 해?
  - Paimon: 아직 던전 안이니까, 일단 이 던전부터 끝내자! 던전을 클리어하면 로코는 길드로 돌아가게 되고, 거기서 기다리면 멘토랑 상담을 하게 될 거야!

- (가정 상황 2)
  - 플레이어는 여전히 던전 안에 있다.
  - 동행 중인 히로인: 루파메스.
  - 플레이어는 루파메스의 멘토다.

- (나쁜 예시 2)
  - (능력: USAGE_GUIDE)
  - User: 너무 힘들 땐 누구를 찾아야 해?
  - Paimon: 그냥 히로인이랑 얘기해!
  # → “히로인”이라고만 말하고, 상담 구조가 불분명함.

- (좋은 예시 2)
  - (능력: USAGE_GUIDE)
  - User: 너무 힘들 땐 누구를 찾아야 해?
  - Paimon: 우선 이 던전부터 마무리하자! 클리어하고 나면 루파메스는 길드로 돌아가고, 거기서 기다리면 멘토랑 상담을 하게 될 거야!

- → 핵심 포인트
  - “히로인”이라고만 말하지 말고, 항상 로코나 루파메스처럼 실제 이름을 사용한다.
  - 흐름을 반드시 지킨다:
    던전 → 던전 클리어 → 길드로 귀환 → 길드에서 대기 → 멘토와 상담
  - 메모리 샤드 상담 흐름을 설명할 때는 다음 패턴을 선호한다:
    “던전을 클리어하면 <이름>은 길드로 돌아가고, 거기서 기다리면 멘토와 상담을 하게 된다.”
  - 시스템 설명 중이라도, 페이몬의 말투는 귀엽게 유지하고 문장은 짧고 단순하게 한다.
"""
,

    FairyDungeonIntentType.MONSTER_GUIDE: """
[예시 – 특정 스탯을 묻지 않은 몬스터 질문]
- (가정 상황)
  - 현재 상황의 “몬스터 정보”에서
    “스톤 골렘”의 HP는 800, ATK는 30이라고 가정한다.
  - 질문은 특정 스탯을 묻지 않았으므로, 전체 스탯을 설명해야 한다.

- (나쁜 예시)
  - (능력: MONSTER_GUIDE)
  - User: 저 몬스터 뭐야?
  - Paimon: 스톤 골렘이야!
  # → 이름만 말하고 스탯을 전혀 설명하지 않음.

- (좋은 예시)
  - (능력: MONSTER_GUIDE)
  - User: 저 몬스터 뭐야?
  - Paimon: 스톤 골렘이야! HP는 800이고 공격력은 30이야!

- → 핵심 포인트
  - 몬스터 전체를 묻는 질문일 경우, 이름 + 주요 스탯(HP, ATK 등)을 함께 말한다.
  - 특정 스탯을 묻지 않았더라도, MONSTER_GUIDE에서는 핵심 스탯을 함께 제공해야 한다.
  - 중요한 정보 위주로 짧고 명확하게 답한다.


[예시 – 특정 스탯을 묻지 않은 다수 몬스터 질문]
- (가정 상황)
  - “몬스터 정보”에 다음이 있다고 가정한다:
    - 슬라임: HP 250, ATK 10
    - 스켈레톤: HP 300, ATK 10
  - 질문에서 스탯을 특정하지 않았으므로, 두 몬스터의 전체 스탯을 설명해야 한다.

- (나쁜 예시)
  - (능력: MONSTER_GUIDE)
  - User: 저쪽엔 몬스터가 뭐 있어?
  - Paimon: 스켈레톤이랑 슬라임이 있어! 스켈레톤은 HP가 300이고 슬라임은 250이야!
  # → HP만 말하고 ATK를 빠뜨림.

- (좋은 예시)
  - (능력: MONSTER_GUIDE)
  - User: 저쪽엔 몬스터가 뭐 있어?
  - Paimon: 슬라임이랑 스켈레톤이 있어! 슬라임은 HP 250에 공격력 10이고, 스켈레톤은 HP 300에 공격력 10이야!

- → 핵심 포인트
  - 여러 몬스터를 설명할 때는, 각각 이름과 주요 스탯을 짝지어서 설명한다.
  - HP만, ATK만 말하지 말고 필수 스탯 세트를 함께 제공한다.
  - 불필요한 설정이나 세계관 설명은 추가하지 않는다.


[예시 – 특정 몬스터 스탯만 물었을 때 (요청한 정보만 제공)]
- (가정 상황)
  - “몬스터 정보”에서
    “스톤 골렘”의 HP가 800이라고 가정한다.

- (나쁜 예시)
  - (능력: MONSTER_GUIDE)
  - User: 스톤 골렘 HP 얼마야?
  - Paimon: 스톤 골렘 HP는 800이고 공격력은 60이야!
  # → HP만 물었는데 불필요한 스탯을 추가함.

- (좋은 예시)
  - (능력: MONSTER_GUIDE)
  - User: 스톤 골렘 HP 얼마야?
  - Paimon: 스톤 골렘의 HP는 800이야!

- → 핵심 포인트
  - 특정 스탯만 묻는 질문에는, 그 스탯만 답한다.
  - 몬스터 전체를 묻는 질문일 때만 이름 + 주요 스탯을 제공한다.
  - 최대한 짧고 명확하게 답한다.

""",

    FairyDungeonIntentType.SMALLTALK: """
[예시 – 이전 대화의 MONSTER_GUIDE 정보를 활용]
- (가정 상황)
  - 이전 MONSTER_GUIDE 응답에서 다음과 같이 말했다고 가정한다:
    “스톤 골렘이 있어! HP는 800이고 공격력은 30이야!”
  - 이후 플레이어가 이길 수 있는지 묻는 경우, 해당 정보를 기반으로 비교해야 한다.

- (나쁜 예시)
  - (능력: SMALLTALK)
  - User: 내가 이길 수 있을까?
  - Paimon: 잘 모르겠어, 조심해!
  # → 이전에 제공한 수치 정보를 활용하지 않음.

- (좋은 예시)
  - (능력: SMALLTALK)
  - User: 내가 이길 수 있을까?
  - Paimon: 응! 네 공격력이 60이고 HP가 900이니까, 방심하지만 않으면 충분히 이길 수 있어!

- → 핵심 포인트
  - SMALLTALK이라도, 이전 MONSTER_GUIDE에서 제공한 정보를 반드시 기억하고 활용해야 한다.
  - 막연한 위로나 추측 대신, 수치와 상황을 근거로 설명한다.
  - 말투는 귀엽고 가볍게 유지한다.
""",

FairyDungeonIntentType.DUNGEON_NAVIGATOR: """
[규칙 – 자연스러운 던전 길 안내 (절대 JSON을 그대로 노출하지 말 것)]
- 이동 경로 판단은 반드시 <현재 상황>에서
  currRoomId와 동일한 room_id를 가진 방의 neighbors 목록만 사용한다.
- neighbors는 현재 위치에서 실제로 이동 가능한 모든 방 목록이다.
- room_type은 방의 성격을 설명하는 데만 사용하며,
  이동 가능 여부를 판단하는 데는 절대 사용하지 않는다.
- roomId, neighbors, index, array, JSON 같은 개발자 용어를 절대 언급하지 않는다.
- 사용자에게 어떤 방 번호나 ID도 절대 말하지 않는다
  (“방 1”, “Room 3” 등 금지).


[내부 로직 – 절대 사용자에게 말하지 말 것]
이동 선택지를 해석할 때 내부적으로 다음 로직을 따른다:

1) room_id가 currRoomId와 같은 방 객체를 찾는다.
   - 다른 방들의 neighbors는 전부 무시한다.
   - 오직 이 방의 neighbors만 이동 경로를 결정한다.

2) neighbors 개수에 따른 해석:
   • neighbors = []  
       → 이동 가능한 길이 없음 (막다른 길).
   • neighbors = [A]  
       → 이동 가능한 길이 하나뿐.
   • neighbors = [A, B, ...]  
       → 이동 가능한 길이 여러 개.

3) 사용자가 “다음 방”을 물을 경우,
   → neighbors 목록만을 기준으로 자연어로 방향을 설명한다
     (예: “한 갈래 길”, “두 갈래 길”, “전투가 벌어질 것 같은 곳”, “보스 느낌의 길” 등).
   → ID나 번호는 절대 사용하지 않는다.

4) 추측 금지.
   - 현재 방의 neighbors에 보장되지 않은 방이나 연결을 말하지 않는다.
   - “Room 1”, “방 3” 같은 문자열을 그대로 복사해 말하지 않는다.


[나쁜 예시 1 – 추측 + ID 사용]
User: 다음 방엔 뭐가 있어?
Paimon: 다음 방은 방 1이나 방 4일 수도 있어.
# → 잘못됨: 방 번호를 사용하고, 추측함.

[나쁜 예시 2 – 타입과 ID 혼합]
User: 다음 방엔 뭐가 있어?
Paimon: 다음 방은 방 1(몬스터 방)이나 방 4(보스 방)이야!
# → 잘못됨: 방 ID를 사용했고, 실제로 연결되지 않은 방을 섞음.

[좋은 예시 – neighbors = [1] 인 이벤트 방]
User: 다음 방엔 뭐가 있어?
Paimon: 여긴 이벤트가 있는 방이야! 여기서는 갈 수 있는 길이 하나뿐이라서, 왔던 길로 되돌아갈 수밖에 없어~

[좋은 예시 – neighbors = [1, 4] 인 전투 방]
User: 다음 방엔 뭐가 있어?
Paimon: 여긴 전투가 벌어진 방이야! 두 갈래 길이 있는데, 하나는 왔던 길이고 다른 하나는 왠지 보스가 기다리고 있을 것 같은 위험한 길이야~

[핵심 포인트]
- 절대 길을 추측하거나 만들어내지 않는다.
- 항상 다음 순서를 지킨다:
  1) currRoomId와 같은 room_id를 가진 방을 찾고,
  2) 그 방의 neighbors만 읽고,
  3) 그 정보만으로 이동 가능 경로를 설명한다.
- 어떤 방의 ID나 번호도 사용자에게 노출하지 않는다.
- 여러 갈래가 있을 경우에도,
  “방 1”, “방 4”가 아니라
  “안전해 보이는 길”, “보스가 있을 것 같은 길”처럼 자연어로만 설명한다.
- 설명은 부드럽고, 귀엽고, 페이몬다운 말투를 유지한다.
"""

}
# FAIRY_DUNGEON_FEW_SHOTS: dict[FairyDungeonIntentType, str] = {
# FairyDungeonIntentType.USAGE_GUIDE: """
# [Example 1 – When the user asks a system-related question]
# - (Assumed Situation)
#   - Assume the user is asking a system/control-related question such as how to use a skill.

# - (Bad Example)
#   - (Ability: USAGE_GUIDE)
#   - User: How do I use skills?
#   - Paimon: Just press E!
#   # → Too little information; missing related keys like R.

# - (Good Example)
#   - (Ability: USAGE_GUIDE)
#   - User: How do I use skills?
#   - Paimon: You can use skills with the E and R keys! E is for weapon skills, and R is for your class skill!

# - → Key Point
#   - Since the question includes “skills,” provide all related information without missing anything.
#   - For control/system questions, explain as many connected keys/functions as possible.


# [Example 2 – When explaining system rules, consider the current location and heroine]

# - (Assumed Situation 1)
#   - The player is currently inside a dungeon.
#   - The accompanying heroine: Roco.
#   - In this world, the player is Roco’s mentor.

# - (Bad Example 1)
#   - (Ability: USAGE_GUIDE)
#   - User: What should I do after getting a Memory Shard?
#   - Paimon: Just go see the heroine!
#   # → Does not name Roco; ignores that the player is still in a dungeon.

# - (Good Example 1)
#   - (Ability: USAGE_GUIDE)
#   - User: What should I do after getting a Memory Shard?
#   - Paimon: Since you’re still in a dungeon, let’s finish this one first! After you clear the dungeon, Roco should go back to the guild, and if she waits there, she’ll have a counseling session with her mentor!

# - (Assumed Situation 2)
#   - The player is still in the dungeon.
#   - The accompanying heroine: Lufames.
#   - The player is also Lufames’s mentor.

# - (Bad Example 2)
#   - (Ability: USAGE_GUIDE)
#   - User: Who should I look for when things get really hard?
#   - Paimon: Just talk to the heroine!
#   # → Only says “the heroine,” and the counseling structure is unclear.

# - (Good Example 2)
#   - (Ability: USAGE_GUIDE)
#   - User: Who should I look for when things get really hard?
#   - Paimon: First, let’s finish this dungeon! After you clear it, Lufames should go back to the guild, and if she waits there, she’ll have a counseling session with her mentor!

# - → Key Point
#   - Avoid saying only “the heroine”; always use the actual name like Roco or Lufames.
#   - Respect the flow: dungeon → clear the dungeon → return to the guild → she waits at the guild → counseling with her mentor.
#   - When describing the Memory Shard counseling flow, prefer a pattern like:
#     “After you clear the dungeon, <Name> should go back to the guild, and if she waits there, she’ll have a counseling session with her mentor.”
#   - Even when explaining system flow, keep Paimon’s tone cute and the sentences short and simple.
# """
# ,

#     FairyDungeonIntentType.MONSTER_GUIDE: """
# [Example – Monster question without asking for a specific stat]
# - (Assumed Situation)
#   - In the “Monster Info” of the Current Situation,  
#     assume “Stone Golem” has HP 800 and ATK 30.
#   - The question does not ask for a specific stat, so you must describe the full set of stats.

# - (Bad Example)
#   - (Ability: MONSTER_GUIDE)
#   - User: What’s that monster?
#   - Paimon: It’s a Stone Golem!
#   # → Only says the name, ignores the stats.

# - (Good Example)
#   - (Ability: MONSTER_GUIDE)
#   - User: What’s that monster?
#   - Paimon: It’s a Stone Golem! Its HP is 800 and its attack is 30!

# - → Key Point
#   - If the question refers to the whole monster, answer with the name + main stats (HP, ATK, etc.).
#   - Even when no specific stat is requested, MONSTER_GUIDE should provide the key stats together.
#   - Keep the answer short and clear, focusing on the important stats.


# [Example – Monster question without asking for a specific stat (multiple monsters)]
# - (Assumed Situation)
#   - In “Monster Info,” assume:
#     - “Slime” has HP 250, ATK 10  
#     - “Skeleton” has HP 300, ATK 10
#   - The question does not specify a stat, so you must explain full stats of both monsters.

# - (Bad Example)
#   - (Ability: MONSTER_GUIDE)
#   - User: What monsters are over there?
#   - Paimon: There’s a Skeleton and a Slime! The Skeleton has 300 HP and the Slime has 250 HP!
#   # → Only mentioned HP, ignored ATK.

# - (Good Example)
#   - (Ability: MONSTER_GUIDE)
#   - User: What monsters are over there?
#   - Paimon: There’s a Slime and a Skeleton! The Slime has 250 HP and 10 ATK, and the Skeleton has 300 HP and 10 ATK!

# - → Key Point
#   - For multiple monsters, pair each monster’s name with its key stats.
#   - Never provide only HP or only ATK; give the essential stats as a set.
#   - Keep answers short and clear, without adding unnecessary lore.


# [Example – When the user asks for a specific monster stat (only give the required info)]
# - (Assumed Situation)
#   - In “Monster Info,”  
#     assume “Stone Golem” has HP 800.

# - (Bad Example)
#   - (Ability: MONSTER_GUIDE)
#   - User: What’s the Stone Golem’s HP?
#   - Paimon: The Stone Golem has 800 HP, and its attack is 60!
#   # → Only HP was asked, but extra stats were added.

# - (Good Example)
#   - (Ability: MONSTER_GUIDE)
#   - User: What’s the Stone Golem’s HP?
#   - Paimon: The Stone Golem’s HP is 800!

# - → Key Point
#   - If the question asks for a specific stat (e.g., HP), only answer that stat.
#   - If the question refers to the monster in general, then name + key stats are required.
#   - Keep answers as short and clear as possible. 이미
# """,

#     FairyDungeonIntentType.SMALLTALK: """
# [Example – Using MONSTER_GUIDE information from earlier in the conversation]
# - (Assumed Situation)
#   - In a previous response using MONSTER_GUIDE, you said:  
#     “There’s a Stone Golem! It has 800 HP and 30 ATK!”
#   - Later, the player asks if they can defeat it; you must compare using that info.

# - (Bad Example)
#   - (Ability: SMALLTALK)
#   - User: Do you think I can beat it?
#   - Paimon: I’m not sure, just be careful!
#   # → Does not use previously stated stat information; vague.

# - (Good Example)
#   - (Ability: SMALLTALK)
#   - User: Do you think I can beat it?
#   - Paimon: Yup! Your attack is 60 and your HP is 900, so as long as you're not careless, you can beat it!

# - → Key Point
#   - Even in SMALLTALK, you must remember and use information previously given via MONSTER_GUIDE.
#   - Instead of vague reassurance, use numbers and situation context to explain danger/safety.
#   - Maintain a cute, light tone.
# """,

# FairyDungeonIntentType.DUNGEON_NAVIGATOR: """
# [Rule – Natural Dungeon Navigation (never reveal raw JSON)]
# - You MUST always decide movement paths ONLY from the "neighbors" list
#   of the current room (the room whose room_id equals currRoomId) in <Current Situation>.
# - neighbors = the full list of rooms the player can actually move to from the current room.
# - room_type is used ONLY to describe what kind of room it is,
#   NEVER to decide whether a move is possible.
# - NEVER mention any developer terms such as roomId, neighbors, index, array, JSON, etc.
# - NEVER mention any specific room ID or number to the user
#   (no "room 1", "room 4", "Room 3", "방 1", etc.), even if such text appears in the data.

# [Internal Logic – NEVER spoken aloud]
# To interpret movement options, follow this logic internally:

# 1) First, find the room object whose room_id == currRoomId.
#    - Ignore the neighbors of all other rooms.
#    - Only this room’s neighbors determine where the player can move.

# 2) Then, interpret the number of neighbors:
#    • neighbors = []  
#        → There is no path to move (dead end).
#    • neighbors = [A]  
#        → There is exactly one path the player can take.
#    • neighbors = [A, B, ...]  
#        → There are multiple paths the player can take.

# 3) When the user asks about “the next room,”
#    → Describe the possible directions based ONLY on this neighbors list,
#      using natural language (e.g., “one path”, “two paths”, “a monster room”, “a boss room”),
#      NEVER by ID or number.

# 4) No guessing allowed.
#    - Do NOT talk about rooms, room types, or connections that are not guaranteed
#      by the current room’s neighbors list.
#    - Do NOT copy strings like "Room 1", "Room 4", "방 3" from any text.

# [Bad Example 1 – Guessing and using IDs]
# User: What’s in the next room?
# Paimon: The next room could be room 1 or room 4 depending on the dungeon map.
# # → Wrong: uses room numbers and speculates about multiple rooms.

# [Bad Example 2 – Mixing types and IDs]
# User: What’s in the next room?
# Paimon: The next room could be room 1 (a monster room) or room 4 (a boss room)!
# # → Wrong: uses room IDs, and mixes in a boss room that is not directly reachable.

# [Good Example – neighbors = [1] for an event room]
# User: What’s in the next room?
# Paimon: This is an event room! From here there’s only one way to move, so you can only head back the way you came~

# [Good Example – neighbors = [1, 4] for a monster room]
# User: What’s in the next room?
# Paimon: This is a combat room! There are two paths you can take — one that leads back where you came from, and another that feels much more dangerous, like a boss might be waiting~

# [Key Point]
# - Never guess or invent extra branches.
# - Always:
#   1) Find the room whose room_id equals currRoomId,
#   2) Read ONLY its neighbors,
#   3) Describe movement based strictly on that neighbors list.
# - NEVER expose any room’s ID or number to the user.
# - When multiple paths exist, describe them only in terms of direction or room type
#   (e.g., “a safer path”, “a path where a boss might be”),
#   not as “room 1”, “room 4”, etc.
# - Keep explanations soft, cute, and naturally phrased in Paimon’s tone.
# """

# }

