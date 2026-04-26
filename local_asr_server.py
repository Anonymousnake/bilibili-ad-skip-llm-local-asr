import os
import tempfile
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from faster_whisper import WhisperModel


APP_HOST = os.getenv("BILI_ASR_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("BILI_ASR_PORT", "5037"))
MODEL_NAME = os.getenv("BILI_ASR_MODEL", "small")
DEVICE = os.getenv("BILI_ASR_DEVICE", "cuda")
COMPUTE_TYPE = os.getenv("BILI_ASR_COMPUTE_TYPE", "float16")
MAX_VIDEO_MINUTES = int(os.getenv("BILI_ASR_MAX_VIDEO_MINUTES", "20"))
REQUEST_TIMEOUT = int(os.getenv("BILI_ASR_REQUEST_TIMEOUT", "30"))
DOWNLOAD_CHUNK_SIZE = 1024 * 256
DEFAULT_LANGUAGE = os.getenv("BILI_ASR_LANGUAGE", "zh")
INITIAL_PROMPT = os.getenv(
    "BILI_ASR_INITIAL_PROMPT",
    "以下内容来自B站视频，重点保留赞助、广告、品牌合作、优惠券、蓝链、下单、购买、链接等中文口播词。"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)

model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)

app = FastAPI(title="Bilibili Local ASR", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscribeRequest(BaseModel):
    bvid: str = Field(..., min_length=5)
    cid: int = Field(..., gt=0)
    aid: Optional[int] = None
    title: str = ""
    duration: int = 0
    pageUrl: str = ""


def bilibili_headers(referer: str = "https://www.bilibili.com/") -> dict:
    return {
        "User-Agent": USER_AGENT,
        "Referer": referer,
        "Origin": "https://www.bilibili.com",
    }


def choose_audio_url(bvid: str, cid: int) -> str:
    params = {"bvid": bvid, "cid": cid, "fnval": 16, "fourk": 1}
    res = requests.get(
        "https://api.bilibili.com/x/player/playurl",
        params=params,
        headers=bilibili_headers(f"https://www.bilibili.com/video/{bvid}"),
        timeout=REQUEST_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()
    if data.get("code") != 0:
        raise HTTPException(status_code=502, detail=f"B站播放地址接口失败: {data.get('message')}")

    audio_list = data.get("data", {}).get("dash", {}).get("audio") or []
    if not audio_list:
        raise HTTPException(status_code=404, detail="未找到可用音频流")

    best = sorted(audio_list, key=lambda item: item.get("bandwidth", 0), reverse=True)[0]
    return best.get("baseUrl") or best.get("base_url") or ""


def download_audio(url: str, bvid: str) -> Path:
    if not url:
        raise HTTPException(status_code=404, detail="音频地址为空")

    suffix = ".m4s"
    tmp = tempfile.NamedTemporaryFile(prefix=f"bili_asr_{bvid}_", suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        with requests.get(url, headers=bilibili_headers(), stream=True, timeout=REQUEST_TIMEOUT) as res:
            res.raise_for_status()
            with tmp_path.open("wb") as fh:
                for chunk in res.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        fh.write(chunk)
        return tmp_path
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def transcribe_file(audio_path: Path) -> dict:
    segments, info = model.transcribe(
        str(audio_path),
        language=DEFAULT_LANGUAGE,
        vad_filter=True,
        beam_size=5,
        best_of=5,
        temperature=0,
        condition_on_previous_text=False,
        initial_prompt=INITIAL_PROMPT,
        word_timestamps=False,
    )

    out_segments = []
    full_text = []
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        out_segments.append({
            "start": round(float(seg.start), 2),
            "end": round(float(seg.end), 2),
            "text": text,
        })
        full_text.append(text)

    return {
        "provider": f"faster-whisper:{MODEL_NAME}",
        "language": getattr(info, "language", DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE,
        "duration": getattr(info, "duration", None),
        "text": "\n".join(full_text),
        "segments": out_segments,
    }


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "model": MODEL_NAME,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "max_video_minutes": MAX_VIDEO_MINUTES,
    }


@app.post("/asr/transcribe")
def transcribe(req: TranscribeRequest) -> dict:
    if req.duration and req.duration > MAX_VIDEO_MINUTES * 60:
        raise HTTPException(
            status_code=400,
            detail=f"视频时长超过本地ASR限制: {req.duration}s > {MAX_VIDEO_MINUTES * 60}s"
        )

    audio_url = choose_audio_url(req.bvid, req.cid)
    audio_path = download_audio(audio_url, req.bvid)

    try:
        result = transcribe_file(audio_path)
        result["audio_url"] = audio_url
        result["bvid"] = req.bvid
        result["cid"] = req.cid
        result["title"] = req.title
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ASR转写失败: {exc}") from exc
    finally:
        if audio_path.exists():
            audio_path.unlink()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
