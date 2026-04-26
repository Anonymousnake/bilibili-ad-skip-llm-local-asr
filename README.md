# B站视频内广告跳过（大模型）

一个基于 Tampermonkey 的 Bilibili 视频广告识别脚本。

它会结合以下信息判断视频是否包含商业推广内容，并在满足条件时自动跳过可定位的植入广告片段：

- 视频标题和简介
- 置顶评论 / 热评
- 弹幕
- 官方 CC 字幕
- 本地 ASR 转写结果（无字幕时可选）
- 大模型分析结果

## 功能概览

- 识别正常视频中的中插广告
- 识别整期推广 / 商单评测 / 导购型视频
- 识别评论区商品卡片、商城跳转、导购链接等强广告信号
- 支持无官方字幕时调用本地 GPU ASR 生成转写文本
- 支持自动跳过已定位的广告片段
- 支持缓存分析结果，减少重复消耗
- 支持多家大模型 API

## 当前目录结构

```text
README.md
README-local-asr.md
requirements-local-asr.txt
local_asr_server.py
B站视频内广告跳过（大模型）.txt
```

## 文件说明

- [B站视频内广告跳过（大模型）.txt](D:/Codex/TamperMonkey/B站视频内广告跳过（大模型）.txt)
  - 脚本主体源码
  - 当前仓库里保留为 `.txt`，便于本地编辑和编码排查
  - 使用时建议复制或重命名为 `.user.js` / `.js`

- [local_asr_server.py](D:/Codex/TamperMonkey/local_asr_server.py)
  - 本地 ASR 服务
  - 使用 `FastAPI + faster-whisper + GPU`

- [requirements-local-asr.txt](D:/Codex/TamperMonkey/requirements-local-asr.txt)
  - 本地 ASR 服务依赖

- [README-local-asr.md](D:/Codex/TamperMonkey/README-local-asr.md)
  - 本地 ASR 单独说明

## 工作流程

1. 脚本读取视频标题、简介、评论、弹幕和字幕。
2. 如果有官方字幕，优先使用官方字幕。
3. 如果没有官方字幕，且启用了本地 ASR，会调用本地服务生成转写文本。
4. 脚本把这些线索发送给大模型做广告类型判断。
5. 如果识别出明确的中插广告区间，且置信度达到阈值，就自动跳过。

## 依赖

### 1. Tampermonkey

需要先在浏览器安装 Tampermonkey。

### 2. 大模型 API

脚本本身不包含可直接使用的分析模型，需要你自己配置：

- OpenAI
- DeepSeek
- Gemini
- Anthropic
- 自定义 OpenAI 兼容接口

### 3. 可选：本地 ASR

如果你希望在“无字幕视频”里也做较完整的识别，可以启用本地 ASR：
- 推荐模型路线：`faster-whisper`

## 使用方式

### 安装脚本

1. 打开 [B站视频内广告跳过（大模型）.txt](D:/Codex/TamperMonkey/B站视频内广告跳过（大模型）.txt)
2. 复制内容
3. 在 Tampermonkey 新建脚本并粘贴

如果你更喜欢标准命名，也可以把这份文件另存为：

```text
B站视频内广告跳过（大模型）.user.js
```

### 配置大模型

双击页面左上角悬浮按钮，打开设置面板，填写：

- API 提供商
- API Key
- 模型名

### 配置本地 ASR

如果你已经运行了本地服务：

- 启用本地 ASR：开启
- 本地 ASR 接口地址：`http://127.0.0.1:5037/asr/transcribe`
- 最长识别视频时长：`20`
- 本地 ASR 超时：`180000`
- 本地 ASR 标识名：例如 `faster-whisper-small`

## 本地 ASR 快速启动

```powershell
Set-Location -LiteralPath 'D:\Codex\TamperMonkey'
python -m venv .venv-asr
.\.venv-asr\Scripts\python.exe -m pip install -r .\requirements-local-asr.txt
.\.venv-asr\Scripts\python.exe .\local_asr_server.py
```

启动后访问：

[http://127.0.0.1:5037/health](http://127.0.0.1:5037/health)

如果返回 `ok: true`，说明本地服务已经正常运行。


## 已知说明

- 这份仓库当前的脚本源码文件后缀是 `.txt`，不是最终分发用的 `.user.js`
- 本地 ASR 服务默认只适合本机单用户使用，没有做鉴权
- 不同视频的 B 站音频流返回结构可能会变化，后续可能还需要继续兼容
