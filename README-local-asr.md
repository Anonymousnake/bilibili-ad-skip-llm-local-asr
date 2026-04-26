# 本地 ASR 服务

这个服务给 `B站视频内广告跳过（大模型）` userscript 提供本地 GPU 转写能力。

## 功能

- 接收 userscript 发来的 `bvid/cid`
- 调 B 站播放地址接口拿音频流
- 下载音频到临时文件
- 用 `faster-whisper` 在本地 GPU 上转写
- 返回全文和分段时间戳

## 适合的机器

- NVIDIA RTX 4060 8GB
- Windows + Python 3.10/3.11

## 安装

先准备一个独立虚拟环境，然后安装依赖：

```powershell
cd D:\Codex\TamperMonkey
python -m venv .venv-asr
.\.venv-asr\Scripts\Activate.ps1
pip install -r .\requirements-local-asr.txt
```

如果你是第一次在这台机器上跑 GPU 版 `faster-whisper`，还需要保证 CUDA 环境和对应依赖已经可用。

## 启动

默认监听 `127.0.0.1:5037`：

```powershell
cd D:\Codex\TamperMonkey
.\.venv-asr\Scripts\python.exe .\local_asr_server.py
```

启动后可以先访问：

```text
http://127.0.0.1:5037/health
```

## 可选环境变量

```powershell
$env:BILI_ASR_MODEL = "medium"
$env:BILI_ASR_DEVICE = "cuda"
$env:BILI_ASR_COMPUTE_TYPE = "float16"
$env:BILI_ASR_MAX_VIDEO_MINUTES = "20"
$env:BILI_ASR_PORT = "5037"
.\.venv-asr\Scripts\python.exe .\local_asr_server.py
```

## 脚本侧推荐设置

- 启用本地 ASR：开启
- 本地 ASR 接口地址：`http://127.0.0.1:5037/asr/transcribe`
- 最长识别视频时长：`20`
- 本地 ASR 超时：`180000`
- 本地 ASR 标识名：`faster-whisper-small` 或 `faster-whisper-medium`

## 返回格式

服务会返回类似：

```json
{
  "provider": "faster-whisper:small",
  "language": "zh",
  "duration": 612.3,
  "text": "完整文本",
  "segments": [
    { "start": 0.0, "end": 5.1, "text": "..." }
  ],
  "audio_url": "https://...",
  "bvid": "BV...",
  "cid": 123456789
}
```

## 注意

- 这是本地单用户服务，没有做鉴权。
- userscript 和本地服务跑在同一台机器上时最合适。
- 如果某些视频拿不到音频流，通常是 B 站接口、地区限制或该视频播放地址结构变化导致的。
