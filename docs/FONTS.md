# 字体

## 画面里的终端字（Python 渲染）

`film/tui_pv_world_execute_20260926/tuikit.py` 用到下面这些字体：

| 变量 | 默认（Windows 自带，不在仓库里） | 用途 | 没有时的替代建议 |
|---|---|---|---|
| `PV_F_MONO` | `C:/Windows/Fonts/consola.ttf` | 等宽正文 | Cascadia Mono、JetBrains Mono |
| `PV_F_MONO_B` | `C:/Windows/Fonts/consolab.ttf` | 等宽粗体 | 同上的 Bold |
| `PV_F_CJK` | `C:/Windows/Fonts/msyh.ttc` | 中文 | Noto Sans SC、Source Han Sans SC |
| `PV_F_SYM` | `C:/Windows/Fonts/seguisym.ttf` | 数学符号（∃ ⟨ ⟩ ⊢ ∀） | Noto Sans Math、DejaVu Sans |

- 在环境变量里把对应的名字设成替代字体文件的路径即可，例如 `PV_F_CJK=/usr/share/fonts/noto/NotoSansSC-Regular.otf`。
- 换了字体，字宽不同，部分排版会轻微错位。
- 标题和横幅用的 Space Mono Bold、Anton 在仓库里（OFL）。

## dsh 窗口里的字（Chromium 渲染）

- 窗口页面照 dsh 前端的 CSS 使用系统界面字体。原片在 Windows 上渲染，中文是微软雅黑。
- 在其他系统上，Chromium 会用系统里的替代字体，换行和行高可能和原片不同。
