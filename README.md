# uv run uvicorn main:app --host 0.0.0.0 --port 9999 --log-level info --access-log
# nohup uv run uvicorn main:app --host 0.0.0.0 --port 9999 --log-level info --access-log   > uvicorn_9999.out 2>&1 &
# tail -f uvicorn_9999.out