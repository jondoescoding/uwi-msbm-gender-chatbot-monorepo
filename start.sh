#!/bin/bash
uvicorn src.server.api.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 120 