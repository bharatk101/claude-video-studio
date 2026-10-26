#!/usr/bin/env bash
# Optional: build whisper.cpp into bin/whisper.cpp with the base.en and small models.
# You only need this for the most accurate caption re-timing (DTW timestamps in retime-captions.py);
# transcription works without it through faster-whisper (pip3 install faster-whisper).
#
#   bash scripts/setup-whisper.sh            # base.en + small
#   MODELS="small" bash scripts/setup-whisper.sh
set -euo pipefail
cd "$(dirname "$0")/.."
MODELS="${MODELS:-base.en small}"
command -v cmake >/dev/null || { echo "needs cmake (brew install cmake / apt install cmake)"; exit 1; }
command -v git >/dev/null || { echo "needs git"; exit 1; }
mkdir -p bin
if [ ! -d bin/whisper.cpp ]; then
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp bin/whisper.cpp
fi
cd bin/whisper.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build build -j --config Release --target whisper-cli
for m in $MODELS; do
  [ -f "models/ggml-$m.bin" ] || bash ./models/download-ggml-model.sh "$m"
done
echo "whisper.cpp ready: bin/whisper.cpp/build/bin/whisper-cli (models: $MODELS)"
