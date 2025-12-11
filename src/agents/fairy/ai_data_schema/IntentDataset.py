import json
import torch
from torch.utils.data import Dataset

class IntentDataset(Dataset):
    def __init__(self, path, tokenizer, label2idx, max_len=64):
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.tokenizer = tokenizer
        self.label2idx = label2idx
        self.num_labels = len(label2idx)
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data[idx]
        text = row["text"]
        labels = row["labels"] 

        inputs = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_len,
            return_tensors="pt"
        )

        label_vec = torch.zeros(self.num_labels)
        for lb in labels:
            label_vec[self.label2idx[lb]] = 1.0

        return {
            "input_ids": inputs["input_ids"].squeeze(0),
            "attention_mask": inputs["attention_mask"].squeeze(0),
            "labels": label_vec  
        }

