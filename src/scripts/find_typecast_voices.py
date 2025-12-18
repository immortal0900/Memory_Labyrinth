"""
Typecast 목소리 조회 스크립트

Typecast API에서 사용 가능한 목소리 목록을 조회하고,
미오, 소라, 새론, 유빈 목소리의 voice_id를 찾습니다.

사용법:
    python -m src.scripts.find_typecast_voices
"""

import os
from typecast.client import Typecast
from dotenv import load_dotenv

load_dotenv()


def find_voices():
    """목소리 목록을 조회하고 원하는 목소리를 찾습니다."""
    
    api_key = os.getenv("TYPECAST_API_KEY")
    if not api_key:
        print("TYPECAST_API_KEY 환경변수가 설정되지 않았습니다.")
        print("먼저 .env 파일에 TYPECAST_API_KEY를 설정하세요.")
        return
    
    # 찾고 싶은 목소리 이름
    target_voices = ["미오", "소라", "새론", "유빈"]
    
    print("=" * 60)
    print("Typecast 목소리 조회")
    print("=" * 60)
    
    # SDK 클라이언트 초기화
    client = Typecast(api_key=api_key)
    
    # 목소리 목록 조회
    voices = client.voices()
    
    print(f"\n총 {len(voices)} 개의 목소리를 찾았습니다.\n")
    
    # 찾은 목소리 저장
    found_voices = {}
    
    for voice in voices:
        voice_id = voice.voice_id
        voice_name = voice.voice_name
        
        # 타겟 목소리인지 확인
        for target in target_voices:
            if target in voice_name:
                found_voices[target] = voice_id
                print(f"[찾음] {target}: {voice_name}")
                print(f"       voice_id: {voice_id}")
                print(f"       emotions: {voice.emotions}")
                print()
    
    print("=" * 60)
    print("결과 요약")
    print("=" * 60)
    
    # NPC 매핑 정보
    npc_mapping = {
        "미오": ("레티아", 1),
        "소라": ("루파메스", 2),
        "새론": ("로코", 3),
        "유빈": ("사트라/대현자", 0),
    }
    
    print("\n# tts_typecast.py의 voice_map에 설정할 값:")
    print("self.voice_map = {")
    
    for target, (npc_name, npc_id) in npc_mapping.items():
        if target in found_voices:
            print(f'    {npc_id}: "{found_voices[target]}",  # {npc_name} - {target}')
        else:
            print(f'    # {npc_id}: "???",  # {npc_name} - {target} (못 찾음)')
    
    print("}")
    
    # 못 찾은 목소리 출력
    not_found = [t for t in target_voices if t not in found_voices]
    if not_found:
        print(f"\n[주의] 다음 목소리를 찾지 못했습니다: {', '.join(not_found)}")
        print("목소리 이름이 다를 수 있습니다. 전체 목록을 확인하세요.")
        print("\n전체 목소리 목록:")
        for voice in voices:
            print(f"  - {voice.voice_name}: {voice.voice_id}")


if __name__ == "__main__":
    find_voices()
