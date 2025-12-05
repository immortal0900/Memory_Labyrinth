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
        # 주의: prompt 내의 일반 JSON 중괄호는 그대로 두고,
        #       input_variables 에 명시된 플레이스홀더만 직접 치환합니다.
        # 변수명 정규화 (공백/따옴표 제거)
        input_vars = [
            str(v).strip().strip('"').strip("'") for v in template.input_variables
        ]

        prompt_text = template.prompt
        for var in input_vars:
            value = cleaned.get(var, "")
            # None 방지 및 문자열 변환
            if not isinstance(value, str):
                try:
                    value = str(value)
                except Exception:
                    value = ""
            # 단일 중괄호 플레이스홀더 치환
            prompt_text = prompt_text.replace(f"{{{var}}}", value)
            # 혹시 남아있을 수 있는 이중 중괄호(템플릿 엔진 호환)도 치환
            prompt_text = prompt_text.replace(f"{{{{{var}}}}}", value)

        return prompt_text
