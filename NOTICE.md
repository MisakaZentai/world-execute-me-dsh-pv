# NOTICE：第三方素材与许可

本仓库的代码按 [LICENSE](LICENSE)（MIT）发布。下面这些不属于那份许可，各自保留原来的许可和权利。

This licence covers the code in this repository (the .py, .mjs and .html files
written for this film). It does not cover the third-party material listed in
NOTICE.md, which keeps its own licence: the whale maid artwork and everything
derived from it (CC BY-NC-SA 4.0), the dsh web frontend files (MIT, DeepSeek),
and the fonts (SIL Open Font License). The song and its lyrics are not part of
this repository.

## 鲸鱼娘立绘与表情（CC BY-NC-SA 4.0）

- **文件**：
  - `film/third_party_references/whale_maid_expanded_20260926/`：`maid-left.webp` 和 `expressions/whale-*.webp`；
  - 由这些图生成的全部画面：`film/pv_dsh_frontend_20260927/avatars/`、`mem_sprites/`；
  - 构建时生成的替身舞者帧；
  - 成片里所有她的形象。
- **署名链**（按 CC BY-NC-SA 4.0 保留完整创作链）：
  1. 角色原作：溟月 © 上善无形（https://www.pixiv.net/users/62155430 ，https://space.bilibili.com/4456176 ）
  2. 女仆版设计：ZipZipPipe（https://www.pixiv.net/users/18604994 ，https://space.bilibili.com/4168597 ）
  3. 立绘：Small-tailqwq / dsh-deep-whale
  4. 八种表情：dsh-whale-galgame（https://github.com/JAdpp/dsh-whale-galgame ）
- **上游原文**：见同目录 `sources/` 里的 NOTICE。许可全文：[LICENSES/CC-BY-NC-SA-4.0.txt](LICENSES/CC-BY-NC-SA-4.0.txt)。
- **作者本人说明**：ZipZipPipe 的 [Pixiv《AI娘化》原帖](https://www.pixiv.net/artworks/148186519)要求署名、非商用，并说明 DeepSeek 娘遵循上善的 CC BY-NC-SA 4.0；2026-09-30 经 Pixiv 公开接口核实。此条款不能推广到该作者其他角色。证据范围见 [docs/ASSET_SOURCES.md](docs/ASSET_SOURCES.md)。
- **本项目的改动**：裁切、缩放、像素化、调色、表情/头像合成、记忆卡片，以及从立绘制作的节拍摆动替身与字符网格。
- **含义**：
  - 使用、改编时保留上面的署名链；
  - 不得商用；
  - 改编作品按同一许可分享。
- 视频中由这些素材改编的部分按 CC BY-NC-SA 4.0 分享。音乐、未包含的 MMD 模型和动作、商标等不因此被重新许可。

## dsh 前端（MIT，Copyright (c) 2026 DeepSeek）

- **文件**：
  - `film/vendor/dsh-web-frontend/`：`@deepseek-ai/dsh-web-frontend` 的两份 CSS 和 index JS，以及它的 `LICENSE`、`package.json`。窗口页面里的图标 SVG 取自这份 JS，`disclosure_map.json` 里的类名也是从它解析出来的。
  - `film/vendor/dsh-client-ui-cordis/`：`@deepseek-ai/dsh-client-ui-cordis` 的 `lib/client.js`，以及它的 `LICENSE`、`package.json`。E 组的 Cordis 行和面板样式从这里读取。
  - `film/pv_dsh_frontend_20260927/dsh_components.css`：从 `@deepseek-ai/dsh-client-ui-*` 的七个包（theme、chat、tool、conversation、message-feedback、deliverables、layout）里抽出的组件样式。这几个包同样是 MIT，Copyright (c) 2026 DeepSeek。
- 这些文件都按各自包的 MIT 许可分发。
- MIT 许可不包括商标：DeepSeek 的名称和标识归其权利人所有。

### 前端 bundle 内的 React 组件

`film/vendor/dsh-web-frontend/dist/assets/index-DuF6ti6g.js` 还包含 React、React JSX runtime、React DOM 和 scheduler 的代码，保留了 Facebook, Inc. and its affiliates 的 MIT 许可标头。对应许可全文另存为 [LICENSES/React-MIT.txt](LICENSES/React-MIT.txt)。DeepSeek 的署名不替代这些上游署名。

## 字体（SIL Open Font License 1.1）

- **文件**：`film/ai_mascot_mv_world_execute_20260926/fonts/`，是 Space Mono Bold 和 Anton Regular。许可文本就在同目录的 `OFL_*.txt`。
- 代码另外用到 Windows 自带的 Consolas、微软雅黑和 Segoe UI Symbol。这些字体**不在**本仓库里，见 [docs/FONTS.md](docs/FONTS.md)。

## 不在本仓库里的

| 东西 | 权利人 | 怎么获得 |
|---|---|---|
| 歌曲 world.execute(me); | Mili | 自备音频，放到 `input/song.mp3`，见 [input/README.md](input/README.md) |
| 歌词 | 歌词作者（Mili） | 构建时由 `tools/lyrics.py fetch` 从 LRCLIB（https://lrclib.net ，条目 36914646）下载到你的本机，或自备 LRC。本仓库只保存不含文字的逐词时间 |
| 原片里的舞者画面 | 基于第三方 MMD 模型和动作生成，AI 参考和衍生画面分发的许可范围尚未确认 | 构建时用鲸鱼娘立绘生成替身帧，见 [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) §舞者 |

音乐按 [Mili 官方使用指引](https://projectmili.com/copyright-guidelines)处理：个人非商业二创可按指引使用；全部或部分含 AI 的同人内容须明确标注。商业用途另行确认。本仓库不授予音乐或歌词的再许可。

## 声明

- 这是非官方同人作品，与 DeepSeek、Mili 及上面列出的各位作者没有从属或合作关系，也未经他们认可。
- 界面致敬 DeepSeek Harness（dsh）的前端。
