# test_full_pipeline.py

## 실행

```bash
cd backend
python -m app.engine.test.test_full_pipeline
```

## STT/TTS 사용 시 추가 설치

### Linux

```bash
# 오디오 재생 (TTS 출력용) - 하나만 설치
sudo apt install mpv          # 권장
# 또는
sudo apt install ffmpeg       # ffplay 포함

# 마이크 녹음 (STT 입력용)
sudo apt install alsa-utils   # arecord 포함
```

### macOS

```bash
# 오디오 재생: 기본 내장 (afplay)
# 마이크 녹음: sox 필요
brew install sox
```

### Windows

기본 내장 플레이어 사용 (추가 설치 불필요)
