import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import keyboard
import time
import requests
import json

SAMPLE_RATE = 16000
OUTPUT_FILE = "record.wav"
JWT = jwt  # 이미 확보한 JWT 토큰 사용


def record_until_key_release():
    print("🎙️ Q 키를 누르는 동안 녹음됩니다…")

    # Q 누를 때까지 대기
    keyboard.wait("q")
    print("🎙️ 녹음 시작!")

    frames = []

    def callback(indata, frames_count, time_info, status):
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        callback=callback,
    )

    stream.start()

    # Q를 떼는 순간까지 녹음
    while keyboard.is_pressed("q"):
        time.sleep(0.01)

    stream.stop()
    stream.close()

    print("🎙️ 녹음 종료!")

    audio_np = np.concatenate(frames, axis=0)
    write(OUTPUT_FILE, SAMPLE_RATE, audio_np)
    print(f"🎧 WAV 저장 완료 → {OUTPUT_FILE}")

    return OUTPUT_FILE


def transcribe_audio(file_path):
    config = {
        "model_name": "sommers",
        "language": "ko",
        "use_paragraph_splitter": True,
    }

    resp = requests.post(
        "https://openapi.vito.ai/v1/transcribe",
        headers={"Authorization": f"Bearer {JWT}"},
        data={"config": json.dumps(config)},
        files={"file": open(file_path, "rb")},
    )

    tid = resp.json().get("id")
    print("📨 업로드 완료 → transcribe_id =", tid)
    return tid


def poll_transcription(transcribe_id):
    print("⏳ 결과 대기 중...")

    while True:
        resp = requests.get(
            f"https://openapi.vito.ai/v1/transcribe/{transcribe_id}",
            headers={"Authorization": f"Bearer {JWT}"},
        )
        data = resp.json()
        status = data.get("status")

        print("현재 상태:", status)

        if status == "completed":
            print("\n===== 🎉 인식 결과 =====")
            for utt in data["results"]["utterances"]:
                print(f"[spk {utt.get('spk', '?')}] {utt['msg']}")
            print("========================\n")
            return

        if status == "failed":
            print("❌ 전사 실패:", data)
            return

        time.sleep(0.3)


# ---------------------------------------------------------
# 전체 흐름
# ---------------------------------------------------------
file = record_until_key_release()
tid = transcribe_audio(file)
poll_transcription(tid)