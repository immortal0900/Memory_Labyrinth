import yaml
from dataclasses import dataclass
from typing import List


@dataclass
class PromptTemplate:
    name: str
    prompt: str
    input_variables: List[str]



class PromptManager:
    def __init__(self, prompt_type):
        self.type = prompt_type
        self._templates = self._load_prompts(prompt_type.value)

    def _load_prompts(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        templates = {}
        enum_class = self.type.__class__

        for key, value in config.items():
            prompt_type = enum_class[key]  # YAML key → Enum key 감지
            templates[prompt_type] = PromptTemplate(
                name=value["name"],
                prompt=value["prompt"],
                input_variables=value.get("input_variables", []),
            )

        return templates

    def get_template(self):
        return self._templates[self.type]

    def get_prompt(self, **kwargs) -> str:
        template = self._templates[self.type]
        cleaned = {k.strip('"').strip("'"): v for k, v in kwargs.items()}
        for var in template.input_variables:
            if var not in cleaned:
                raise ValueError(f"Missing required variable '{var}' for {template.name}")

        # 변수 치환
        try:
            return template.prompt.format(**cleaned)
        except KeyError as e:
            missing = str(e).strip("'\"")
            return template.prompt.replace(f"{{{missing}}}", "")
