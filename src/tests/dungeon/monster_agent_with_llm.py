import json
import os
import random
from typing import List, Dict, Tuple, Any
from langchain_openai import ChatOpenAI
from models import MonsterMetadata, StatData, RoomData, MonsterSpawnData
from enums.LLM import LLM
from prompts.promptmanager import PromptManager
from prompts.prompt_type.dungeon.DungeonPromptType import DungeonPromptType

class MonsterCompositionAgent:
    """
    [MonsterCompositionAgent]
    역할: 언리얼에서 받은 정보를 가지고 몬스터를 채워 넣는 에이전트

    구조
    1. Brain(LLM) : 현재 던전 히로인 상태를 분석하여 '난이도 배율'과 '추천 태그'를 결정 (전략 수립)
    2. Body(Algo) : 결정된 전략에 따라 실제 DB 에서 몬스터를 선별하고 좌표를 생성 (실행)
    """

    def __init__(self, hero_stats: List[StatData], monster_db: Dict[int, MonsterMetadata], model_name: str = LLM.GPT4_1_NANO):
        self.hero_stats = hero_stats
        self.monster_db = monster_db

        # 1. LLM 초기화
        self.llm = self._initialize_llm(model_name)
        # 2. 프롬프트 매니저 초기화( YAML 파일 로드)
        self.prompt_manager = PromptManager(DungeonPromptType.MONSTER_STRATEGY)

    def _initialize_llm(self, model_name: str):
        """
        모델 이름(Enum)에 따라 API Key와 Base URL을 설정하여 LLM 객체 생성
        """
        api_key = ""
        base_url = None 

        # GPT (OpenAI)
        if "gpt" in model_name:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = None # OpenAI 기본값 사용

        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            base_url=base_url,
            temperature=0.7 # 창의성 조절 (0.0 ~ 1.0)
        )

    def _calculate_party_score(self) -> float:
        """
        히로인 파티의 평균 전투력 계산
        (models.py의 StatData.combat_score 프로퍼티 활용)
        """
        if not self.hero_stats: return 0.0
        total_score = sum(h.combat_score for h in self.hero_stats)
        return total_score / len(self.hero_stats)

        
    def _get_llm_strategy(self, party_score: float, floor: int) -> Dict:
        """
        [Brain] LLM에게 히로인 정보를 주고 밸런싱 전략(JSON)을 받아옴
        """
        hero = self.hero_stats[0] # 대표 히로인 (또는 평균값 사용 가능)
        
        # 1. YAML에 정의된 변수({hero_summary})에 넣을 요약 문자열 생성
        hero_summary = (
            f"HP: {hero.hp}, "
            f"Strength: {hero.strength}, "
            f"Dexterity: {hero.dexterity}, "
            f"CombatScore: {party_score:.1f}"
        )

        try:
            # 2. PromptManager를 통해 완성된 프롬프트 문자열 생성
            # monster_strategy.yaml의 {hero_summary}, {floor} 구멍을 채웁니다.
            final_prompt = self.prompt_manager.get_prompt(
                hero_summary=hero_summary,
                floor=floor
            )
            
            # 3. LLM 호출
            response = self.llm.invoke(final_prompt)
            
            # 4. 응답 파싱 (JSON 문자열 -> Python Dict)
            # 가끔 LLM이 ```json ... ``` 형태로 줄 때가 있어 이를 제거합니다.
            content = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
            
        except Exception as e:
            print(f"[LLM Error] 전략 수립 실패 (Fallback 작동): {e}")
            # 에러 발생 시 기본 전략 반환 (안전장치)
            return {
                "difficulty_multiplier": 1.2, 
                "preferred_tags": [], 
                "reasoning": "LLM 응답 실패로 기본값 적용"
            }

    def _select_monsters(self, target_score: float, preferred_tags: List[str]) -> List[MonsterMetadata]:
        """
        [Body] 타겟 점수와 태그에 맞는 몬스터 후보군 선정
        """
        candidates = []
        
        # 1. 점수 기반 1차 필터링 (오차범위 ±30%)
        for m in self.monster_db.values():
            if target_score * 0.7 <= m.cost_point <= target_score * 1.3:
                candidates.append(m)
        
        # 2. 태그 가중치 적용 (확률 조작)
        # preferred_tags에 해당하는 몬스터는 리스트에 여러 번 넣어 당첨 확률을 높임
        weighted_pool = []
        if candidates:
            for m in candidates:
                weight = 1
                # (확장성) 추후 몬스터 데이터에 tags가 있다면 아래 주석 해제
                # if any(tag in m.tags for tag in preferred_tags): weight = 5 
                weighted_pool.extend([m] * weight)
        else:
            # 조건에 맞는 몬스터가 없으면 Cost가 가장 낮은 3마리 반환 (최소한의 방어)
            weighted_pool = sorted(self.monster_db.values(), key=lambda x: x.cost_point)[:3]
            
        return weighted_pool

    def _generate_coordinate(self) -> Tuple[float, float]:
        """
        [좌표 생성] 0.1 ~ 0.9 사이의 랜덤 좌표 생성
        벽(0.0, 1.0)에 끼이지 않도록 여유를 둠
        """
        x = random.uniform(0.1, 0.9)
        y = random.uniform(0.1, 0.9)
        return (round(x, 2), round(y, 2))

    def process_dungeon(self, dungeon_json: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        [메인 실행 함수]
        LangGraph Node에서 호출되는 진입점
        """
        
        # 1. 히로인 전투력 계산
        party_score = self._calculate_party_score()
        
        # 2. [Brain] LLM에게 전략 수립 요청 (현재 2층이라고 가정)
        # 실제로는 dungeon_json이나 state에서 floor 정보를 가져와야 함
        current_floor = 2 
        strategy = self._get_llm_strategy(party_score, current_floor)
        
        multiplier = strategy.get("difficulty_multiplier", 1.2)
        tags = strategy.get("preferred_tags", [])
        reasoning = strategy.get("reasoning", "")
        
        # 3. [Body] 목표 몬스터 점수 확정
        target_score = party_score * multiplier
        
        # 4. 몬스터 배치 실행
        updated_rooms = []
        raw_rooms = dungeon_json.get("rooms", [])
        
        # 전략에 맞는 후보군 미리 생성 (Pool)
        candidate_pool = self._select_monsters(target_score, tags)
        
        for room_dict in raw_rooms:
            # Dict -> 객체 변환
            room = RoomData.from_dict(room_dict)
            
            # 전투방(Type 1)이고 몬스터가 비어있으면 -> 채워넣기
            if room.room_type == 1 and not room.monsters:
                spawn_list = []
                # 방 크기에 비례해 마릿수 결정 (Size 3 -> 3~4마리)
                count = random.randint(room.size, room.size + 1)
                
                for _ in range(count):
                    # 후보군에서 랜덤 뽑기
                    mob = random.choice(candidate_pool)
                    # 좌표 생성
                    gx, gy = self._generate_coordinate()
                    
                    spawn_list.append(MonsterSpawnData(
                        monster_id=mob.monster_id,
                        pos_x=gx,
                        pos_y=gy
                    ))
                
                room.monsters = spawn_list
            
            # 객체 -> Dict 변환 후 리스트 추가
            updated_rooms.append(room.to_dict())
            
        # 원본 JSON 데이터 업데이트
        dungeon_json["rooms"] = updated_rooms
        
        # 로그(Log) 생성 (디버깅용)
        log = {
            "model_used": self.llm.model_name,
            "hero_score": party_score,
            "ai_multiplier": multiplier,
            "ai_reasoning": reasoning,
            "target_score": target_score,
            "preferred_tags": tags
        }
        
        return dungeon_json, log

