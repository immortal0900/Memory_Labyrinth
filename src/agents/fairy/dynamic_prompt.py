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