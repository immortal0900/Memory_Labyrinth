# 요정 API 수정

(배포시 알파버전 패키징 파일에서 정령 테스트는 불가합니다.   
AI 팀은 어느정도 테스트 완료했으므로 새로 배포합니다.)   

정령 기능 바뀐점 
- 상호작용 과거 참고 대화 강화
- 무기를 FinalDamage 기준으로 추천 
- 불필요 데이터 참고 제거

## 1. 정령 - 던전 대화
`POST /dungeon/talk`

### 요청 방식 (Body)

| Field                           | Type           | Required | Description                       |
| :------------------------------ | :------------- | :------- | :-------------------------------- |
| `dungeonPlayer`                 | Object         | Yes      | 던전 플레이어의 **실시간 상태 데이터**     |
| ├── `playerId`                  | String         | Yes      | 플레이어 고유 ID                      |
| ├── `heroineId`                 | Integer        | Yes      | 히로인의 고유 ID                      |
| ├── `currRoomId`                | Integer        | Yes      | 현재 위치한 방 ID                     |
| ├── `difficulty`                | Integer        | Yes      | 던전 난이도 (기본값: 0)                |
| ├── `stats`                     | Object         | Yes      | 플레이어의 전투·이동·스킬 관련 **스탯 데이터** |
| │   ├── `hp`                    | Integer        | Yes      | 현재 체력 (기본값: 250)                |
| │   ├── `moveSpeed`             | Float          | Yes      | 이동 속도 배율 (기본값: 1.0)           |
| │   ├── `attackSpeed`           | Float          | Yes      | 공격 속도 배율 (기본값: 1.0)           |
| │   ├── `cooldownReduction`     | Float          | Yes      | 쿨타임 감소 배율                      |
| │   ├── `strength`              | Integer        | Yes      | 근력                                |
| │   ├── `dexterity`             | Integer        | Yes      | 기량                                |
| │   ├── `intelligence`          | Integer | null | No       | 지능 (기본값: Null)                   | 
| │   ├── `critChance`            | Float          | No      | 치명타 확률 20 ~ 100                  |
| │   ├── `skillDamageMultiplier` | No          | Yes      | 스킬 피해 증가(곱연산) 1 ~ 5            |
| │   └── `autoAttackMultiplier`  | No          | Yes      | 평타 피해 증가 (곱연산) 1 ~ 5           |
| ├── `weaponId`                  | Integer        | No      | 장착 중인 무기 ID                      |
| ├── `skillIds`                  | List[int]      | No      | 플레이어가 보유한 스킬 ID 목록             |
| └── `inventory`                 | List[int]      | No      | 인벤토리에 포함된 아이템 ID 목록           |
| `question`                      | String         | Yes      | 사용자의 질문 (예: `"현재 방의 불좀 켜줘"`)  |
| `targetMonsterIds`              | List[int]      | No       | 타겟팅된 몬스터 ID 목록 (기본값: `[]`)      |
| `nextRoomIds`                   | List[int]      | No      | 히로인이 이동 가능한 방 ID 목록 (기본값: `[]`) |

### 요청 예시 
```json
{
    "dungeonPlayer": {
        "playerId": "TEST0",
        "heroineId": 1,
        "currRoomId": 3,
        "difficulty": 0,
        "stats":{
            "hp": 250,
            "moveSpeed": 1.0,
            "attackSpeed": 1.0,
            "cooldownReduction" : 1,
            "strength": 8,
            "dexterity": 1,
            "intelligence": null,
            "critChance": 20.0,
            "skillDamageMultiplier" : 1.0,
            "autoAttackMultiplier": 1.0
        },
        "skillIds":[0,1],
        "weaponId": 21,
        "inventory": [
            0,
            22,
            42
        ]
    },
    "question": "이제 뭐해?",
    "targetMonsterIds": [],
    "nextRoomIds": [0,1]
}
```
dungeonPlayer 수정:  hp, moveSpeed, attackSpeed 는 stats 객체로 옮겻고 subWeaponId 제거했습니다.
dungeonPlayer.stats 추가:  stats 데이터는 데이터 스프레트시트에 표기된 내용과 똑같이 맞췄습니다.
dungeonPlayer.skillIds 추가: 히로인 스킬 id 목록을 하나로 퉁쳤습니다. 히로인이 가진 skill id 를 모두 넘겨주시면 됩니다.

응답(Response)는 기존과 같습니다.

## 2. 정령 - 상호작용
`POST /dungeon/interaction`

#### 요청 방식 (Body)

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `question`                      | String         | Yes      | 사용자의 질문                         |
| `dungeonPlayer`                 | Object         | Yes      | 던전 플레이어의 **실시간 상태 데이터**     |
| ├── `playerId`                  | String         | Yes      | 플레이어 고유 ID                      |
| ├── `heroineId`                 | Integer        | Yes      | 히로인의 고유 ID                      |
| ├── `currRoomId`                | Integer        | Yes      | 현재 위치한 방 ID                     |
| ├── `difficulty`                | Integer        | Yes      | 던전 난이도 (기본값: 0)                |
| ├── `stats`                     | Object         | Yes      | 플레이어의 전투·이동·스킬 관련 **스탯 데이터** |
| │   ├── `hp`                    | Integer        | Yes      | 현재 체력 (기본값: 250)                |
| │   ├── `moveSpeed`             | Float          | Yes      | 이동 속도 배율 (기본값: 1.0)           |
| │   ├── `attackSpeed`           | Float          | Yes      | 공격 속도 배율 (기본값: 1.0)           |
| │   ├── `cooldownReduction`     | Float          | Yes      | 쿨타임 감소 배율                      |
| │   ├── `strength`              | Integer        | Yes      | 근력                                |
| │   ├── `dexterity`             | Integer        | Yes      | 기량                                |
| │   ├── `intelligence`          | Integer | null | No       | 지능 (기본값: Null)                   | 
| │   ├── `critChance`            | Float          | No      | 치명타 확률 20 ~ 100                  |
| │   ├── `skillDamageMultiplier` | No          | Yes      | 스킬 피해 증가(곱연산) 1 ~ 5            |
| │   └── `autoAttackMultiplier`  | No          | Yes      | 평타 피해 증가 (곱연산) 1 ~ 5           |
| ├── `weaponId`                  | Integer        | No      | 장착 중인 무기 ID                      |
| ├── `skillIds`                      | List[int]      | No      | 플레이어가 보유한 스킬 ID 목록             |
| └── `inventory`                 | List[int]      | No      | 인벤토리에 포함된 아이템 ID 목록           |


```json
{
  "question": "가장 좋은거 써줘",
  "dungeonPlayer": {
        "playerId": "76561198301668617",
        "heroineId": 1,
        "currRoomId": 1,
        "difficulty": 0,
        "stats":{
            "hp": 250,
            "moveSpeed": 1.0,
            "attackSpeed": 1.0,
            "cooldownReduction" : 1,
            "strength": 8,
            "dexterity": 1,
            "intelligence": null,
            "critChance": 20.0,
            "skillDamageMultiplier" : 1.0,
            "autoAttackMultiplier": 1.0
        },
        "skillIds":[0,1],
        "weaponId": 21,
        "inventory": [
            0,
            22,
            42
        ]
  }
}
```
dungeonPlayer 추가: 정령 던전 대화 API 와 똑같은 dungeonPlayer 객체를 보내주시면 됩니다.
dungeonPlayer 가 추가됨으로 가장 바깥에 있던 inventory 필드는 삭제했습니다.   

응답(Response)는 기존과 같습니다.