#!/usr/bin/env bash
set -euo pipefail

PORT=9999
LOG_FILE="uvicorn_${PORT}.out"

echo "== 1) Kill GPU compute procs matching ProjectML/.venv/bin/python3 =="

# nvidia-smi에서 PID 뽑기 (없으면 빈 문자열)
GPU_PIDS="$(
  nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>/dev/null \
  | awk -F',' '$2 ~ /ProjectML\/\.venv\/bin\/python3/ {gsub(/ /,"",$1); print $1}' \
  | tr '\n' ' ' || true
)"

if [[ -n "${GPU_PIDS// }" ]]; then
  echo "GPU PIDs: ${GPU_PIDS}"
  # 내 권한으로 먼저 시도, 안 되면 sudo로 재시도
    # 1) 먼저 우아하게 종료(SIGTERM)
  kill ${GPU_PIDS} 2>/dev/null || sudo kill ${GPU_PIDS} 2>/dev/null || true

  # 2) 잠깐 기다렸다가 아직 살아있으면 강제 종료(SIGKILL)
  sleep 2
  for p in ${GPU_PIDS}; do
    if kill -0 "$p" 2>/dev/null; then
      sudo kill -9 "$p" 2>/dev/null || true
    fi
  done
else
  echo "No matching GPU processes found."
fi

echo
echo "== 2) Kill LISTEN process on TCP port ${PORT} =="

# netstat 출력에서 PID 추출 (없으면 빈 문자열)
PORT_PIDS="$(
  sudo netstat -ltnp 2>/dev/null \
  | awk -v p=":${PORT}" '$4 ~ p && $6 == "LISTEN" {split($7,a,"/"); if(a[1]!="-" && a[1]!="") print a[1]}' \
  | sort -u \
  | tr '\n' ' ' || true
)"

if [[ -n "${PORT_PIDS// }" ]]; then
  echo "Port ${PORT} LISTEN PIDs: ${PORT_PIDS}"
  sudo kill -9 ${PORT_PIDS} || true
else
  echo "No LISTEN process found on port ${PORT}."
fi

echo
echo "== 3) Start uvicorn on port ${PORT} with nohup (log: ${LOG_FILE}) =="

# (선택) 스크립트 위치 기준으로 실행하고 싶으면 주석 해제
# cd "$(dirname "$0")"

nohup uv run uvicorn main:app --host 0.0.0.0 --port ${PORT} --log-level info --access-log \
  > "${LOG_FILE}" 2>&1 &

NEW_PID=$!
echo "Started uvicorn (PID=${NEW_PID})"
echo
echo "== 4) Tail logs (Ctrl+C to stop tail; server keeps running) =="

exec tail -f "${LOG_FILE}"
