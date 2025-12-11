import torch.nn as nn
from kobert_transformers import get_kobert_model

class KoBertMultiLabelClassifier(nn.Module):
    def __init__(self, num_labels):
        super().__init__()
        self.bert = get_kobert_model()
        hidden_size = 768 

        self.classifier = nn.Linear(hidden_size, num_labels)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        pooled = outputs[1] 

        logits = self.classifier(pooled)
        return logits