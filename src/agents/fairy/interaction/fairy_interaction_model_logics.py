from core.common import get_inventory_items
from typing import List
import numpy as np
from FlagEmbedding import BGEM3FlagModel
from core.game_dto.z_cache_data import cache_items
from core.game_dto.ItemData import ItemData

emb_model = BGEM3FlagModel("BAAI/bge-m3")
class ItemEmbeddingLogic:

    def __init__(self):
        self.ITEM_VEC_CACHE = {}
    #     self._init_item_vectors()

    # def _item_text(self, item: ItemData) -> str:
    #     w = item.weapon        
    #     return (
    #         f"{item.itemName} {w.attackPower} {w.staggerPower} {w.rarity} {w.modifier}"
    #     )

    # def _init_item_vectors(self):
    #     texts = [self._item_text(item) for item in cache_items]
    #     vecs = emb_model.encode(texts)["dense_vecs"]
    #     for item, vec in zip(cache_items, vecs):
    #         self.ITEM_VEC_CACHE[item.itemId] = vec

    # def _cosine(self, a, b):
    #     return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    # def pick_items(
    #     self, question: str, inventory_ids: List[int], top_k: int = 4
    # ) -> List[int]:
    #     items = get_inventory_items(inventory_ids)
    #     if not items:
    #         return []

    #     # 질문 임베딩 1회
    #     q_vec = emb_model.encode([question])["dense_vecs"][0]
    #     sims = []

    #     for item in items:
    #         item_vec = self.ITEM_VEC_CACHE[item.itemId]
    #         sim = self._cosine(q_vec, item_vec)
    #         sims.append((item.itemId, sim))

    #     # 유사도 높은 순으로 정렬 (index 0 = 가장 유사)
    #     sims.sort(key=lambda x: x[1], reverse=True)
    #     filtered = [item_id for item_id, sim in sims if sim >= 0.2]
    #     return filtered[:top_k]


class IsItemUseEmbeddingLogic:
    def __init__(self):
        self.TRUE_SENTENCES = [
            "장비를 장착해",
            "무기를 장착해",
            "검을 장착해",
            "대검을 장비해",
            "쌍검을 장비해",
            "둔기를 장착해",
            "현재 무기를 교체해",
            "장비를 교체해",
            "더 강한 무기를 장착해",
            "공격력이 높은 무기를 사용해",
            "방금 획득한 무기를 장비해",
            "가장 강한 장비를 장착해",
            "전투용 무기를 사용해",
            "전투용 무기를 써줘",
            "지금 무기를 장착해",
            "장비를 즉시 착용해",
            "새 장비를 사용해",
            "새 장비를 써줘",
            "장착 가능한 무기를 장비해",
            "무기 슬롯을 변경해",
            "방어력이 높은 장비를 착용해",
            "방어력이 높은 장비를 써줄래?",
            "공격 속도가 빠른 무기를 장착해",
            "현재보다 좋은 무기를 사용해",
            "무기를 바로 장착해",
            "전투에 적합한 무기를 장비해",
            "가장 높은 등급의 무기를 사용해",
            "레전드 무기를 장착해",
            "레어 장비를 장착해",
            "고급 무기를 사용해",
            "고급 무기를 써줄래?",
            "균형잡힌 무기를 장착해",
            "힘 기반 무기를 사용해",
            "민첩 기반 장비를 장착해",
            "민첩 기반 장비를 써줄래?",
            "장비 슬롯을 교체해",
            "더 나은 무기로 바꿔",
            "더 나은 무기로 바꿔줘",
            "새로운 장비를 착용해",
            "스탯이 높은 무기를 장비해",
            "주 무기를 교체해",
            "적합한 장비를 장착해",
            "주요 무기를 사용해",
            "원하는 무기를 장비해",
            "선택한 무기를 장착해",
            "전투 준비를 위해 무기를 장비해",
            "그 무기 써줘",
            "저 아이템 써줘",
            "그러면 그걸 사용해",
            "그럼 그거 사용해"            
        ]
        self.FALSE_SENTENCES = [
            "장비 목록을 보여줘",
            "무기 옵션을 설명해줘",
            "장비 능력치를 알려줘",
            "어떤 무기를 들고 있는지 보여줘",
            "장비는 어디서 얻어?",
            "이 장비는 얼마나 강해?",
            "무기 효과는 어떻게 적용돼?",
            "레전드 무기는 어디에서 드랍돼?",
            "장비 등급을 비교해줘",
            "무기를 사용하면 얼마나 강해질까?",
            "장비의 내구도는 어떻게 돼?",
            "무기 역사에 대해 알려줘",
            "장비가 얼마나 희귀한지 궁금해",
            "다음 장비는 언제 얻을 수 있어?",
            "무기 강화 시스템이 어떻게 돼?",
            "장비 효과를 상세히 설명해줘",
            "무기를 착용하면 어떤 스탯이 오르지?",
            "레어 장비는 어떤 특징이 있어?",
            "장비 교체가 좋은 선택일까?",
            "무기의 추천 조합이 뭐야?",
            "장비는 어디에서 파밍하는 게 좋아?",
            "이 무기의 설명을 알려줘",
            "장비 교체 조건이 뭐야?",
            "장비 세부 옵션을 분석해줘",
            "이 무기의 드랍률은 어떻게 돼?",
            "장비를 사용하는 게 좋을까?",
            "무기 옵션이 어떻게 구성돼?",
            "장비 착용 가능 레벨은 뭐야?",
            "고급 장비는 얼마나 비싸?",
            "무기 스토리를 알려줘",
            "장비 성능을 평가해줘",
            "무기를 사용할 수 있는 조건은 뭐야?",
            "어떤 장비가 좋은지 추천해줘",
            "이 무기를 지금 사용해야 할까?",
            "이 장비는 어떤 스타일에 어울려?",
            "무기 타입 차이를 알려줘",
            "장비 효과 발동 조건이 뭐야?",
            "무기의 숨겨진 옵션이 있나?",
            "장비를 사용하면 부작용이 있나?",
            "장비 스탯 계산 방식을 설명해줘",
        ]
        self.TRUE_VEC = self._mean_vec(self.TRUE_SENTENCES)
        self.FALSE_VEC = self._mean_vec(self.FALSE_SENTENCES)

    def _mean_vec(self, texts):
        vecs = emb_model.encode(texts)["dense_vecs"]
        return np.mean(vecs, axis=0)
    
    def _cosine(self, a, b):
        return float(a @ b / (np.linalg.norm(a)*np.linalg.norm(b) + 1e-8))

    def is_item_use(self, sentence: str) -> bool:
        vec = emb_model.encode([sentence])["dense_vecs"][0]
        sim_true = self._cosine(vec, self.TRUE_VEC)
        sim_false = self._cosine(vec, self.FALSE_VEC)
        return sim_true > sim_false




import torch
from typing import List
from huggingface_hub import hf_hub_download
from kobert_transformers import get_tokenizer
from agents.fairy.ai_data_schema.KoBertMultiLabelClassifier import KoBertMultiLabelClassifier
from agents.fairy.fairy_state import FairyInterationIntentType

class FairyInteractionIntentModel:
    def __init__(
        self,
        repo_id: str = "JINSUP/ProjectML-Models",
        filename: str = "fairy_interaction_intent_kobert_classifier.pt",
        device: str = "cpu"
    ):
        self.repo_id = repo_id
        self.filename = filename
        self.device = device

        self.weight_path = hf_hub_download(
            repo_id=self.repo_id,
            filename=self.filename
        )

        checkpoint = torch.load(self.weight_path, map_location=device)

        self.idx2label = checkpoint["idx2label"]
        num_labels = len(self.idx2label)

        self.model = KoBertMultiLabelClassifier(num_labels=num_labels)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        self.tokenizer = get_tokenizer()

    def predict(self, text: str):
        """
        text → labels, probabilities 반환
        """

        inputs = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=64,
            return_tensors="pt"
        )

        input_ids = inputs["input_ids"]
        attention_mask = inputs["attention_mask"]

        with torch.no_grad():
            logits = self.model(input_ids, attention_mask)
            probs = torch.sigmoid(logits).squeeze(0)

        preds = (probs > 0.5).nonzero().flatten().tolist()
        labels = [self.idx2label[p] for p in preds]

        return labels, probs.cpu().tolist()
    
    @staticmethod
    def parse_intents_to_enum(raw):
        import ast
        
        if isinstance(raw, str):
            raw = ast.literal_eval(raw)
        
        enums = []
        for label in raw:
            try:
                enums.append(FairyInterationIntentType(label))
            except ValueError:
                enums.append(FairyInterationIntentType.NONE)
        return enums
    


