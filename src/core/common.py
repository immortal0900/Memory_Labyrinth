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
"""
import json
def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        

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
    

from core.game_dto.z_cache_data import items
from core.game_dto.ItemData import ItemData
from typing import List
def get_inventory_items(inventory_ids:list) -> List[ItemData]:
    return [item for item in items if item.itemId in inventory_ids]

def get_inventory_item(item_id: int):
    for item in items:
        if item.itemId == item_id:
            return item
    return None

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