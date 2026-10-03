# world.execute(me); · 大肥鱼眼中的 world.execute(me)

![preview](docs/preview.jpg)

一支用代码逐帧渲染的 TUI 风格 PV，**非官方同人作品**：
- 左边是 DeepSeek Harness（dsh）的聊天窗口，她和"你"的对话；
- 右边是运行着她的那个世界，也就是模型的可视化。

这个仓库是这支片子的全部出片代码。你自备歌曲，一条命令就能从头渲染出来。

- 成片：[B 站 BV1xCai6aE9g](https://www.bilibili.com/video/BV1xCai6aE9g/)（原舞者版；开源重建差异见下文）
- 作者：MisakaZentai

*English: the complete source of a code-rendered, unofficial fan PV for Mili's "world.execute(me);". Every frame is a
pure function of song time. On the left is a DeepSeek Harness chat window, rendered as per-frame HTML pages built
from dsh's own CSS and screenshotted with Playwright. On the right is a TUI model-visualisation engine drawn with
PIL. Bring your own copy of the song, then run `python build.py all`. The code is MIT; the artwork is
CC BY-NC-SA 4.0; the song and lyrics are not included (see NOTICE.md).*

## 快速开始

需要：
- Python 3.12+，装上 `pip install -r requirements.txt`；
- Node 20+；
- ffmpeg（在 PATH 里）；
- Windows 字体。在别的系统上可以换字体，见 [docs/FONTS.md](docs/FONTS.md)。

```
npm install
npx playwright install chromium
# 把歌曲放到 input/song.mp3（见 input/README.md）
python build.py all            # 检查 → 歌词 → 替身舞者 → 页面截图 → 渲染
python build.py all --4k       # 另出 3840×2160 版
```

- **输出**：`out/film.mp4` 是 1280×720 成片；`out/film_master.mp4` 是无损母版；加 `--4k` 时另有 `out/film_4k.mp4`。
- **耗时**：CPU 渲染全片大约十几分钟到半小时，取决于核数。有 CUDA 版 torch 时，加 `--gpu --python <那个 python>` 会快很多。
- **分步**：每一步也可以单独跑，`python build.py <check|lyrics|dancer|pages|render>`。

## 不在仓库里的，以及替代办法

| 东西 | 为什么 | 替代办法 |
|---|---|---|
| 歌曲音频 | Mili 的版权 | 自备，放到 `input/song.mp3`；`build.py check` 用 sha256 核对版本 |
| 歌词原文 | 歌词版权 | `build.py lyrics` 从 LRCLIB 下载到你的本机，再和仓库里的逐词时间（不含文字）合成 |
| 原片的舞者画面 | 涉及第三方 MMD 模型和动作的使用条件；AI 参考与衍生画面分发权限尚未确认 | 构建时用鲸鱼娘立绘生成替身，所以你渲染出的片子在这些地方和原片不同 |
| Consolas、微软雅黑等 Windows 字体 | 不可再分发 | 用本机的；其他系统可以换字体 |

## 重建出的片子和成片的差别

- **舞者**：见上表，用替身。
- **12.5–29 秒的检查点编号**：数字和成片不同。成片用的这段窗口截图，比代码里最后一次改编号公式要早。
- **123.5 秒前后 3 帧**：输入框的发送按钮颜色不同。原因同上。
- **后期差异（原因未核实）**：既有比对在 114.75–114.83 秒发现局部亮度差，在 159–161 秒最左两列发现约 10 级差值。CPU/GPU 后期实现不同是可能原因，尚未做控制变量验证。
- **验证范围**：2026-09-30 的既有 Windows 构建记录包含 4968 张窗口截图和全片母版数值比对，人工抽看 8 个时刻。母版差异筛选条件为“差值超过 8 级的像素占比超过 0.2%”；这不表示每个像素差值都在 8 级以内，也不等于逐帧视觉或音画验收。测试借用了已有 Playwright 环境，尚未证明全新安装及其他系统能复现相同排版。

## 仓库结构

目录名保留了制作时的工作名，代码之间靠相对位置互相找到，请不要改名。

| 路径 | 内容 |
|---|---|
| `build.py` | 一键出片 |
| `tools/` | 歌词合成（`lyrics.py`）、替身舞者（`placeholder_h3.py`） |
| `data/` | 不含文字的逐词时间、歌曲指纹、舞者帧的清单 |
| `film/pv_dsh_frontend_20260927/` | 左边的 dsh 窗口：各组页面脚本 `batch_*.py`、截图脚本 `seg_shot.mjs`、合成与补丁 `dsh_her.py`、`dsh_patch_*.py` |
| `film/tui_pv_world_execute_20260926/` | 右边的 TUI 引擎：`tuikit.py`，第一版镜头 `full/`，第二版连续性和转场 `continuity_full_v2/` 等 |
| `film/mmd_motion_eval_20260927/pv_full.py` | 舞者的时间表 |
| `film/third_party_references/` | 鲸鱼娘立绘和表情（CC BY-NC-SA 4.0） |
| `film/vendor/` | dsh 前端（`dsh-web-frontend`）和 Cordis 组件包（`dsh-client-ui-cordis`）的 CSS 和 JS（MIT，DeepSeek） |
| `docs/` | [制作原理](docs/HOW_IT_WORKS.md)、[字体](docs/FONTS.md) |

## 许可

- **代码**：MIT，见 [LICENSE](LICENSE)。
- **美术**：鲸鱼娘立绘、表情及它们的改编部分按 CC BY-NC-SA 4.0 分享。使用时保留署名链和许可链接，注明改动，不得商用，改编部分按同协议分享。此声明不授予音乐、其他模型/动作或商标的权利。
- **dsh 前端文件**：MIT，Copyright (c) 2026 DeepSeek。
- **字体**：SIL OFL 1.1。

第三方清单见 [NOTICE.md](NOTICE.md)，一手授权来源和核实范围见 [docs/ASSET_SOURCES.md](docs/ASSET_SOURCES.md)。

## 分享视频

- 本项目使用了 AI 生成的角色美术；原片另含 AI 视频画面。发布相应成片时应明确标注包含 AI 生成内容，不能把纯代码渲染误写为全部画面均非 AI。
- Mili 的[官方指引](https://projectmili.com/copyright-guidelines)允许个人非商业二创，并要求 AI 同人内容明确标注。音乐与歌词的权利保留，不适用本仓库代码的 MIT 许可。
- 默认按非商业方式分享，保留完整素材署名和许可链接；商单、付费观看或收益计划等用途需另外确认。
- 原定稿舞者的 AI 参考权限仍有开放问题。开源重建使用替身；替身方案不表示原定稿已获得额外许可。
- 歌词短前缀是定位时间的实现方式；“连续五词扫描”仅是内容检查规则，不能作为版权免责标准。

## 署名

- **音乐**：Mili - world.execute(me);
- **角色**：溟月 © 上善无形 / 女仆版 ZipZipPipe / 立绘 dsh-deep-whale（Small-tailqwq）/ 表情 dsh-whale-galgame
- **界面**：致敬 DeepSeek Harness（dsh）前端
- **灵感**：野生大K《GPT6-Astra眼中的world.execute(me)》；仓库的组织方式参考了 [pdoom-video](https://github.com/mexicat/pdoom-video)
- **歌词数据**：LRCLIB（构建时下载，不随仓库分发）

这是非官方同人作品，与 DeepSeek、Mili 没有从属或合作关系，也未经他们认可。
