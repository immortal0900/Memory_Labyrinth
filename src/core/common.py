from pathlib import Path
import os
import torch

def get_project_root() -> Path:
    current_path = Path(__file__).resolve()
    marker_files = ['.git', 'pyproject.toml', 'requirements.txt']
    for parent in current_path.parents:
        if any((parent / marker).exists() for marker in marker_files):
            return parent
    return Path(os.getcwd())

def get_src_path(*paths):
    return get_project_root() / "src" / Path(*paths)

def get_data_path(*paths):
    return get_project_root() / "src" / "data" / Path(*paths)

from datetime import datetime
from zoneinfo import ZoneInfo
def get_today_str(pattern: str = "%Y-%m-%d") -> str:
    tz: str = "Asia/Seoul"
    return datetime.now(ZoneInfo(tz)).strftime(pattern)

def get_cur_timestamp():
    return int(datetime.now().timestamp())


"""사용예시:
read_json(get_data_path() / "data"/"test.json") 
write_json("data/test.json", json_data)

read_jsonl(get_data_path() / "data"/"test.json") 
write_jsonl("data/test.json", json_data)
"""
import json
def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
def write_jsonl(path, data):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]
    

"""사용 예시: 
find_files(get_data_path(), patterns=("*.pdf", "*.xml"))
find_files(get_project_root(),/"src"/"data", patterns=("*.pdf", "*.xml"))

주의: patterns가 1개일 경우 튜플로 감싸면서 뒤에 , 를 필수로 넣을 것
find_files(get_data_path(), patterns=("*.json",))
find_files(get_project_root() / "src"/"data" , patterns=("*.json",))
"""

from pathlib import Path
def find_files(base, patterns=("*",)):
    base = Path(base)
    files = []
    for p in patterns:
        files.extend(base.rglob(p))
    return sorted(files)

def get_best_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    else:
        return torch.device("cpu")
    

from core.game_dto.z_cache_data import cache_items
from core.game_dto.ItemData import ItemData
from typing import List

from core.game_dto.StatData import StatData
from core.game_dto.WeaponData import WeaponData

from typing import Optional

def _calculate_final_damage_score(
    stat: StatData,
    weapon: WeaponData,
) -> float:
    stat_contribution = 0.0
    for stat_name, ratio in weapon.modifier.items():
        v = getattr(stat, stat_name, 0) or 0
        stat_contribution += v * ratio 

    effective_multiplier = (stat.autoAttackMultiplier + stat.skillDamageMultiplier) / 2

    return stat_contribution * weapon.attackPower * effective_multiplier

# def get_inventory_items(inventory_ids:list) -> List[ItemData]:
#     return [item for item in cache_items if item.itemId in inventory_ids]

from typing import List

def get_inventory_items(
    inventory_ids: list[int],
    stat: StatData
) -> List[ItemData]:
    result: List[ItemData] = []

    for item in cache_items:
        if item.itemId not in inventory_ids:
            continue

        if item.weapon is not None:
            weapon = item.weapon
            final_damage = _calculate_final_damage_score(stat, weapon)
            weapon.finalDamage = final_damage

        result.append(item)
    result.sort(
        key=lambda item: item.weapon.finalDamage if item.weapon else -1.0,
        reverse=True
    )
    return result

def get_inventory_item(item_id: int, stat: StatData):
    for item in cache_items:
        if item.itemId != item_id:
            continue

        # weapon 이 있는 경우에만 계산
        if item.weapon is not None:
            final_damage = _calculate_final_damage_score(stat, item.weapon)
            item.weapon.finalDamage = final_damage

        return item

    return None

from core.game_dto.SkillData import SkillData
from core.game_dto.z_cache_data import cache_skills
def get_skills(skills_ids:List[int]) -> List[SkillData]:
    result: List[SkillData] = []
    for skill in cache_skills:
        if skill.skillId not in skills_ids:
            continue
        result.append(skill)
    return result
    


# 아래는 주피터 노트북에서 src 경로를 고정시키기위한 코드 
# import os, sys
# from pathlib import Path

# def find_src_folder():
#     current = Path(os.getcwd()).resolve()
#     for p in [current] + list(current.parents):
#         src = p / "src"
#         if src.exists():
#             return src
#     raise RuntimeError("src 폴더를 찾을 수 없습니다.")

# src_path = find_src_folder()
# sys.path.append(str(src_path))