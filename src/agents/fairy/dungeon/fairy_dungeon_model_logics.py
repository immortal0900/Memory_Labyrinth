import torch
from typing import List
from huggingface_hub import hf_hub_download
from kobert_transformers import get_tokenizer
from agents.fairy.ai_data_schema.KoBertMultiLabelClassifier import KoBertMultiLabelClassifier
from agents.fairy.fairy_state import  FairyDungeonIntentType
class FairyDungeonIntentModel:
    def __init__(
        self,
        repo_id: str = "JINSUP/ProjectML-Models",
        filename: str = "fairy_dungeon_intent_kobert_model.pt",
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
                enums.append(FairyDungeonIntentType(label))
            except ValueError:
                enums.append(FairyDungeonIntentType.UNKNOWN_INTENT)
        return enums
    


