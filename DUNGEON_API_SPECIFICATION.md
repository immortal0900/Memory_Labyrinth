# Dungeon API 명세서

## 개요
언리얼 엔진과 FastAPI 서버 간 던전 시스템 통신 프로토콜입니다.

**Base URL**: `http://localhost:8090`

---

## 1. 던전 입장 (Entrance)

### Endpoint
```
POST /api/dungeon/entrance
```

### 설명
던전에 입장하여 1, 2, 3층을 생성합니다.

### Request Body
```json
{
    "rawMap": {
        "playerIds": [0],
        "heroineIds": [1],
        "rooms": [
            {
                "roomId": 0,
                "type": 0,
                "size": 4,
                "neighbors": [1],
                "monsters": [],
                "eventType": 0
            },
            {
                "roomId": 1,
                "type": 2,
                "size": 4,
                "neighbors": [0, 2],
                "monsters": [],
                "eventType": 0
            },
            {
                "roomId": 2,
                "type": 1,
                "size": 10,
                "neighbors": [3, 1],
                "monsters": [{"monsterId": 0, "posX": 0.5, "posY": 8.5}],
                "eventType": 1
            },
            {
                "roomId": 3,
                "type": 1,
                "size": 12,
                "neighbors": [4, 2],
                "monsters": [{"monsterId": 0, "posX": 10.5, "posY": 14.5}],
                "eventType": 2
            },
            {
                "roomId": 4,
                "type": 4,
                "size": 12,
                "neighbors": [3],
                "monsters": [],
                "eventType": 0
            }
        ],
        "rewards": []
    }
}
```

#### Request Schema
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `rawMap` | object | ✓ | 던전 맵 데이터 |
| `rawMap.playerIds` | array[int] | ✓ | 플레이어 ID 목록 |
| `rawMap.heroineIds` | array[int] | ✓ | 히로인 ID 목록 |
| `rawMap.rooms` | array[Room] | ✓ | 방 정보 목록 |
| `rawMap.rewards` | array[int] | | 보상 목록 (기본값: []) |

#### Room Schema
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `roomId` | int | ✓ | 방 고유 ID |
| `type` | int | ✓ | 방 타입 (0=empty, 1=monster, 2=event, 3=treasure, 4=boss) |
| `size` | int | ✓ | 방 크기 |
| `neighbors` | array[int] | ✓ | 인접한 방 ID 목록 |
| `monsters` | array[Monster] | | 몬스터 목록 (기본값: []) |
| `eventType` | int | | 이벤트 타입 (기본값: 0) |

#### Monster Schema
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `monsterId` | int | ✓ | 몬스터 ID |
| `posX` | float | ✓ | X 좌표 |
| `posY` | float | ✓ | Y 좌표 |

### Response
```json
{
    "success": true,
    "message": "던전 입장 성공",
    "floorIds": {
        "floor1": 1,
        "floor2": 2,
        "floor3": 3
    }
}
```

#### Response Schema
| 필드 | 타입 | 설명 |
|------|------|------|
| `success` | boolean | 성공 여부 |
| `message` | string | 응답 메시지 |
| `floorIds` | object | 생성된 층 ID 맵핑 |
| `floorIds.floor1` | int | 1층 ID |
| `floorIds.floor2` | int | 2층 ID |
| `floorIds.floor3` | int | 3층 ID |

### Error Response
```json
{
    "detail": "던전 입장 실패: {error_message}"
}
```

---

## 2. 던전 밸런싱 (Balance)

### Endpoint
```
POST /api/dungeon/balance
```

### 설명
보스방 진입 시 Super Agent를 실행하여 던전 밸런싱을 수행합니다.

### Request Body
```json
{
    "dungeonId": 1,
    "heroineData": {
        "heroine_id": "1",
        "name": "레티아",
        "event_room": 3,
        "memory_progress": 40
    },
    "heroineStat": {
        "hp": 300,
        "strength": 50,
        "dexterity": 15,
        "intelligence": 10,
        "defense": 20,
        "critChance": 15.0,
        "attackSpeed": 1.5,
        "moveSpeed": 500,
        "skillDamageMultiplier": 1.2
    },
    "heroineMemories": [],
    "dungeonPlayerData": {
        "affection": 50,
        "sanity": 80,
        "difficulty_level": "normal"
    },
    "usedEvents": []
}
```

#### Request Schema
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `dungeonId` | int | ✓ | 던전 ID |
| `heroineData` | object | ✓ | 히로인 데이터 |
| `heroineData.heroine_id` | string | ✓ | 히로인 ID |
| `heroineData.name` | string | ✓ | 히로인 이름 |
| `heroineData.event_room` | int | ✓ | 이벤트 발생 방 번호 |
| `heroineData.memory_progress` | int | ✓ | 메모리 진행도 (0-100) |
| `heroineStat` | object | ✓ | 히로인 스탯 |
| `heroineStat.hp` | int | ✓ | 체력 |
| `heroineStat.strength` | int | ✓ | 힘 |
| `heroineStat.dexterity` | int | ✓ | 민첩 |
| `heroineStat.intelligence` | int | ✓ | 지능 |
| `heroineStat.defense` | int | ✓ | 방어력 |
| `heroineStat.critChance` | float | ✓ | 치명타 확률 (%) |
| `heroineStat.attackSpeed` | float | ✓ | 공격 속도 |
| `heroineStat.moveSpeed` | int | ✓ | 이동 속도 |
| `heroineStat.skillDamageMultiplier` | float | ✓ | 스킬 데미지 배율 |
| `heroineMemories` | array | | 히로인 메모리 목록 (기본값: []) |
| `dungeonPlayerData` | object | ✓ | 던전 플레이어 데이터 |
| `dungeonPlayerData.affection` | int | ✓ | 호감도 (0-100) |
| `dungeonPlayerData.sanity` | int | ✓ | 정신력 (0-100) |
| `dungeonPlayerData.difficulty_level` | string | ✓ | 난이도 (easy/normal/hard) |
| `usedEvents` | array | | 이미 사용한 이벤트 목록 (기본값: []) |

### Response
```json
{
    "success": true,
    "message": "밸런싱 완료",
    "dungeonId": 1,
    "agentResult": {
        "dungeon_data": {
            "dungeon_id": 1,
            "floor_count": 1,
            "rooms": [
                {
                    "size": 4,
                    "neighbors": [1],
                    "monsters": [],
                    "room_id": 0,
                    "room_type": "empty",
                    "event_type": 0
                },
                {
                    "size": 4,
                    "neighbors": [0, 2],
                    "monsters": [],
                    "room_id": 1,
                    "room_type": "event",
                    "event_type": 0
                },
                {
                    "size": 10,
                    "neighbors": [3, 1],
                    "monsters": [1, 1],
                    "room_id": 2,
                    "room_type": "monster",
                    "event_type": 1
                },
                {
                    "size": 12,
                    "neighbors": [4, 2],
                    "monsters": [1],
                    "room_id": 3,
                    "room_type": "monster",
                    "event_type": 2
                },
                {
                    "size": 12,
                    "neighbors": [3],
                    "monsters": [100],
                    "room_id": 4,
                    "room_type": "boss",
                    "event_type": 0
                }
            ]
        },
        "events": {
            "main_event": {
                "title": "떨쳐내기 힘든 유혹",
                "event_code": "IRRESISTIBLE_TEMPTATION",
                "is_personal": true,
                "scenario_text": "방에 입장하면 화면이 검은색으로 채워진다. 당신의 눈앞에는, 당신이 좋아하는 것들이 등장하며 당신을 그쪽으로 다가가도록 유도한다."
            },
            "sub_event": {
                "narrative": "문지방을 넘기는 순간, 시야가 완전히 먹빛으로 잠긴다. 방의 형태도, 바닥의 경계도 사라진 채 끝없는 암흑뿐이다. 그 어둠 속에서, 당신이 가장 약해지는 지점을 정확히 찌르는 유혹들이 하나씩 떠오른다.\n\n손을 뻗으면 닿을 것처럼 가까운 곳에, 당신이 평소 갈망하던 무기와 방어구, 디멘시움으로 가득 찬 상자가 아른거린다. 다른 한편엔 고통 없이 쉬어갈 수 있다며, 따뜻한 침상과 안락한 불빛이 당신을 부드럽게 부른다. 속삭임 같은 목소리가 귓가를 파고든다. "괜찮아… 지금은 그냥, 원하는 걸 받아들이기만 해…" 어둠은 당신이 움직이기만을 기다리며, 유혹의 형상을 더욱 또렷이 만들어 간다.",
                "choices": [
                    {
                        "action": "눈앞의 보상을 집어 들고, 유혹을 그대로 받아들인다",
                        "reward_id": "item_reward_uncommon",
                        "penalty_id": "curse_debuff"
                    },
                    {
                        "action": "유혹을 뿌리치고, 눈을 감은 채 한 걸음 앞으로 나아간다",
                        "reward_id": "hp_increase_all",
                        "penalty_id": null
                    },
                    {
                        "action": "차분히 숨을 고르며, 유혹의 형상을 끝까지 관찰한다",
                        "reward_id": "dexterity_increase_all",
                        "penalty_id": "instant_damage_low"
                    }
                ],
                "expected_outcome": "1) 유혹을 그대로 받아들이면 언커먼 아이템을 얻어 당장의 전투력이 상승하지만, 저주 디버프가 걸려 일정 시간 동안 스킬 데미지가 감소해 강력한 스킬 위주의 전투가 크게 약화된다.\n2) 유혹을 뿌리치고 앞으로 나아가면 최대 체력이 영구적으로 증가해 생존력이 높아지며, 추가적인 패널티는 없다. 대신 즉각적인 아이템 이득은 얻지 못한다.\n3) 끝까지 관찰하면 기량이 상승해 명중률과 회피, 정밀한 조작이 유리해지지만, 정신적 부담이 육체적 충격으로 돌아와 고정 피해를 입어 현재 체력이 감소한다."
            },
            "event_room_index": 3
        },
        "monster_stats": {
            "total_count": 4,
            "boss_count": 1,
            "normal_count": 3
        },
        "difficulty_info": {
            "combat_score": 146.0,
            "ai_multiplier": 0.9
        }
    }
}
```

#### Response Schema
| 필드 | 타입 | 설명 |
|------|------|------|
| `success` | boolean | 성공 여부 |
| `message` | string | 응답 메시지 |
| `dungeonId` | int | 던전 ID |
| `agentResult` | object | AI 에이전트 밸런싱 결과 |
| `agentResult.dungeon_data` | object | 밸런싱된 던전 데이터 |
| `agentResult.dungeon_data.dungeon_id` | int | 던전 ID |
| `agentResult.dungeon_data.floor_count` | int | 층 번호 |
| `agentResult.dungeon_data.rooms` | array[Room] | 밸런싱된 방 목록 |
| `agentResult.events` | object | 이벤트 정보 |
| `agentResult.events.main_event` | object | 메인 이벤트 |
| `agentResult.events.main_event.title` | string | 이벤트 제목 |
| `agentResult.events.main_event.event_code` | string | 이벤트 코드 |
| `agentResult.events.main_event.is_personal` | boolean | 개인 이벤트 여부 |
| `agentResult.events.main_event.scenario_text` | string | 이벤트 시나리오 텍스트 |
| `agentResult.events.sub_event` | object | 서브 이벤트 |
| `agentResult.events.sub_event.narrative` | string | 이벤트 내러티브 |
| `agentResult.events.sub_event.choices` | array[Choice] | 선택지 목록 |
| `agentResult.events.sub_event.expected_outcome` | string | 예상 결과 설명 |
| `agentResult.events.event_room_index` | int | 이벤트 발생 방 인덱스 |
| `agentResult.monster_stats` | object | 몬스터 통계 |
| `agentResult.monster_stats.total_count` | int | 총 몬스터 수 |
| `agentResult.monster_stats.boss_count` | int | 보스 몬스터 수 |
| `agentResult.monster_stats.normal_count` | int | 일반 몬스터 수 |
| `agentResult.difficulty_info` | object | 난이도 정보 |
| `agentResult.difficulty_info.combat_score` | float | 전투 점수 |
| `agentResult.difficulty_info.ai_multiplier` | float | AI 배율 |

#### Balanced Room Schema
| 필드 | 타입 | 설명 |
|------|------|------|
| `room_id` | int | 방 ID |
| `room_type` | string | 방 타입 (empty/monster/event/treasure/boss) |
| `size` | int | 방 크기 |
| `neighbors` | array[int] | 인접 방 ID 목록 |
| `monsters` | array[int] | 몬스터 ID 목록 |
| `event_type` | int | 이벤트 타입 |

#### Choice Schema
| 필드 | 타입 | 설명 |
|------|------|------|
| `action` | string | 선택지 행동 설명 |
| `reward_id` | string | 보상 ID |
| `penalty_id` | string \| null | 패널티 ID (없으면 null) |

### Error Response
```json
{
    "detail": "밸런싱 실패: {error_message}"
}
```

---

## 3. 층 완료 (Clear)

### Endpoint
```
PUT /api/dungeon/clear
```

### 설명
현재 층을 완료 처리합니다 (is_finishing=TRUE).

### Request Body
```json
{
    "playerIds": [0]
}
```

#### Request Schema
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `playerIds` | array[int] | ✓ | 플레이어 ID 목록 |

### Response
```json
{
    "success": true,
    "message": "1층 완료",
    "finishedFloor": 1,
    "balancedMap": {
        "dungeon_id": 1,
        "floor_count": 1
    }
}
```

#### Response Schema
| 필드 | 타입 | 설명 |
|------|------|------|
| `success` | boolean | 성공 여부 |
| `message` | string | 응답 메시지 |
| `finishedFloor` | int | 완료된 층 번호 |
| `balancedMap` | object | 밸런싱된 맵 정보 |
| `balancedMap.dungeon_id` | int | 던전 ID |
| `balancedMap.floor_count` | int | 완료된 층 번호 |

### Error Response
```json
{
    "detail": "층 완료 처리 실패: {error_message}"
}
```

## 데이터 흐름

```
1. 던전 입장 (Entrance)
   ↓
2. 층 진행 (게임 플레이)
   ↓
3. 보스방 입장 시 밸런싱 (Balance)
   ↓
4. 층 완료 (Clear)
   ↓
5. 다음 층으로 이동 또는 던전 종료
```

### 처리 순서
1. **POST /api/dungeon/entrance**: 던전 시작, 1~3층 생성
2. **POST /api/dungeon/balance**: 각 층의 보스방 입장 전 밸런싱 수행
3. **PUT /api/dungeon/clear**: 층 완료 후 다음 층으로 진행

---