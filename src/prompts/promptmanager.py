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
                raise ValueError(
                    f"Missing required variable '{var}' for {template.name}"
                )

        # 변수 치환 (JSON/{} 보존을 위해 안전 치환)
        input_vars = [
            str(v).strip().strip('"').strip("'") for v in template.input_variables
        ]

        prompt_text = template.prompt
        for var in input_vars:
            value = cleaned.get(var, "")
            if not isinstance(value, str):
                try:
                    value = str(value)
                except Exception:
                    value = ""
            prompt_text = prompt_text.replace(f"{{{var}}}", value)
            prompt_text = prompt_text.replace(f"{{{{{var}}}}}", value)

        # 치환 후에도 플레이스홀더가 남아있으면 에러 발생
        for var in input_vars:
            if f"{{{var}}}" in prompt_text or f"{{{{{var}}}}}" in prompt_text:
                raise ValueError(
                    f"Prompt variable '{{{var}}}' was not replaced in template '{template.name}'.\n"
                    f"Check if you passed the correct argument and value."
                )

        return prompt_text
