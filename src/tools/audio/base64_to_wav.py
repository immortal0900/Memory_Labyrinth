"""
Base64 오디오 데이터를 WAV 파일로 변환하는 유틸리티

사용법:
    # 모듈로 사용
    from tools.audio.base64_to_wav import base64_to_wav, save_base64_as_wav
    
    wav_bytes = base64_to_wav(audio_base64_string)
    save_base64_as_wav(audio_base64_string, "output.wav")
    
    # CLI로 사용
    python -m tools.audio.base64_to_wav <base64_string> <output_path>
    python -m tools.audio.base64_to_wav --file <json_file> <output_dir>
"""

import base64
import json
import sys
from pathlib import Path
from typing import Union


def base64_to_wav(audio_base64: str) -> bytes:
    """Base64 인코딩된 오디오 데이터를 WAV 바이트로 디코딩
    
    Args:
        audio_base64: Base64로 인코딩된 WAV 오디오 문자열
        
    Returns:
        디코딩된 WAV 바이트 데이터
    """
    return base64.b64decode(audio_base64)


def save_base64_as_wav(audio_base64: str, output_path: Union[str, Path]) -> Path:
    """Base64 오디오 데이터를 WAV 파일로 저장
    
    Args:
        audio_base64: Base64로 인코딩된 WAV 오디오 문자열
        output_path: 저장할 파일 경로
        
    Returns:
        저장된 파일의 Path 객체
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    wav_bytes = base64_to_wav(audio_base64)
    
    with open(output_path, "wb") as f:
        f.write(wav_bytes)
    
    print(f"[OK] WAV 파일 저장됨: {output_path} ({len(wav_bytes):,} bytes)")
    return output_path


def extract_audio_from_response(response_json: dict, output_dir: Union[str, Path]) -> list[Path]:
    """API 응답 JSON에서 audio_base64를 추출하여 WAV 파일로 저장
    
    히로인 채팅, 대현자 채팅, 히로인간 대화 응답 모두 지원
    
    Args:
        response_json: API 응답 JSON (dict)
        output_dir: WAV 파일을 저장할 디렉토리
        
    Returns:
        저장된 WAV 파일 경로 리스트
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files = []
    
    # 히로인간 대화 응답 (conversation 배열이 있는 경우)
    if "conversation" in response_json:
        for idx, turn in enumerate(response_json["conversation"]):
            if "audio_base64" in turn:
                speaker = turn.get("speaker_name", f"speaker_{turn.get('speaker_id', idx)}")
                filename = f"turn_{idx:02d}_{speaker}.wav"
                filepath = save_base64_as_wav(turn["audio_base64"], output_dir / filename)
                saved_files.append(filepath)
    
    # 단일 응답 (히로인/대현자 채팅)
    elif "audio_base64" in response_json:
        text_preview = response_json.get("text", "response")[:20].replace(" ", "_")
        filename = f"response_{text_preview}.wav"
        # 파일명에서 유효하지 않은 문자 제거
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        filepath = save_base64_as_wav(response_json["audio_base64"], output_dir / filename)
        saved_files.append(filepath)
    
    return saved_files


def main():
    """CLI 진입점"""
    if len(sys.argv) < 3:
        print("사용법:")
        print("  직접 변환: python -m tools.audio.base64_to_wav <base64_string> <output.wav>")
        print("  JSON 파일: python -m tools.audio.base64_to_wav --file <response.json> <output_dir>")
        print("")
        print("예시:")
        print("  python -m tools.audio.base64_to_wav UklGRv... output.wav")
        print("  python -m tools.audio.base64_to_wav --file response.json ./audio_output/")
        sys.exit(1)
    
    if sys.argv[1] == "--file":
        # JSON 파일에서 추출
        json_path = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "./audio_output"
        
        with open(json_path, "r", encoding="utf-8") as f:
            response_json = json.load(f)
        
        saved_files = extract_audio_from_response(response_json, output_dir)
        print(f"\n총 {len(saved_files)}개 WAV 파일 저장됨")
        
    else:
        # 직접 Base64 문자열 변환
        audio_base64 = sys.argv[1]
        output_path = sys.argv[2]
        save_base64_as_wav(audio_base64, output_path)


if __name__ == "__main__":
    main()

