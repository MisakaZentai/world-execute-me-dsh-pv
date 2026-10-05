# 60 帧导出：插帧流程、文件大小与内存

项目原始画布是 **1280×720、24 fps**。完成无损 RGB 母版后，可以用 FFmpeg 做运动补偿插帧，再导出 1080p 或 2K 的 60 fps 播放版。本文中的“2K”沿用常见显示器称呼，指 **2560×1440（1440p / QHD）**。

本文记录 2026-10-04 的实际导出流程和 2026-10-05 核对的成片数据，并给出独立的后处理命令。它补充现有构建流程；`build.py` 的默认画布、帧率和命令行选项保持原有行为。

## 实际生成了什么

各文件时长均为 **211.916667 秒**。大小采用十进制 MB，即 1 MB = 1,000,000 字节；视频码率来自 `ffprobe` 的视频流 `bit_rate`。

| 输出 | 分辨率 / 帧率 | 视频编码 | 视频平均码率 | 文件大小 | 相比 720p 播放版 |
|---|---|---|---:|---:|---:|
| `out/film.mp4` | 1280×720 / 24 fps | H.264，CRF 12，slow | 3.916 Mbps | 112.457 MB | 基准 |
| `out/film_1080p60.mp4` | 1920×1080 / 60 fps | H.264，CRF 18，medium，VBV 4.5 Mbps / 9 Mbit | 4.531 Mbps | 128.930 MB | +14.65% |
| `out/film_2k60.mp4` | 2560×1440 / 60 fps | H.264，CRF 18，medium，VBV 8 Mbps / 16 Mbit | 7.667 Mbps | 211.993 MB | +88.51% |
| `out/film_4k.mp4` | 3840×2160 / 24 fps | HEVC 10-bit，CRF 10，medium | 20.647 Mbps | 555.662 MB | +394.11% |

四份播放版使用同一份 AAC 混音：44.1 kHz、双声道，设定 320 kbps，实测平均约 323 kbps，包含歌曲和结尾提示音。

这些是**本次本地导出的配置与测量值**。项目默认 `build.py` 的 720p 与 4K 播放版均使用 CRF 16；上表的 CRF 12 / 10 是本次采用的设置。因此“1080p 60 帧只大约 15%”描述这一组输出，不能直接推广到默认构建或其他视频。

插帧输入是 `out/film_master.mp4`：720p、24 fps、5086 帧，无损 RGB 视频。此次带配乐母版约 693.889 MB，含 24-bit ALAC 音轨；它与上表有损播放版的用途、像素格式和音频编码不同。

## 1. 60 帧是怎样生成的

### 先插帧，再放大

本次处理顺序如下：

1. 读取已经完成的 720p 无损 RGB 母版。原有 Python 绘图、角色缓存和 Playwright 截图不需要重跑。
2. 用 BT.709 矩阵将画面转换成有限范围的 `yuv420p`，在 **720p** 上估计相邻帧之间的运动。
3. 用 `minterpolate` 在每个 1/60 秒的目标时刻生成画面。
4. 用 Lanczos 将结果放大到 1920×1080 或 2560×1440，然后编码为 H.264。
5. 按时间顺序连接视频分段，直接复制已对齐的 AAC 音轨。歌曲速度、起点和结尾提示音的位置保持不变。

运动估计在原始 720p 上进行，可以减少估计阶段需要处理的像素和中间数据。放大后的空间细节仍来自 720p 母版；插帧主要增加时间采样。

### 实际使用的插帧参数

```text
minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:mb_size=16:search_param=16:vsbmc=1:scd=fdiff:scd_threshold=5
```

| 参数 | 在本次流程中的作用 |
|---|---|
| `fps=60` | 目标时间网格为每秒 60 帧 |
| `mi_mode=mci` | 根据估计的运动合成中间画面 |
| `mc_mode=aobmc` | 对重叠的运动块做自适应加权 |
| `me_mode=bidir` | 在前后两个方向估计运动 |
| `me=epzs` | 使用 EPZS 搜索算法 |
| `mb_size=16`、`search_param=16` | 本次使用的运动块与搜索参数 |
| `vsbmc=1` | 开启可变块尺寸补偿，细化物体边界 |
| `scd=fdiff`、`scd_threshold=5` | 根据帧差检测切镜；命中时用重复帧代替跨镜头运动插值 |

这里的运动补偿由 FFmpeg 执行，本次没有使用神经网络插帧模型。切镜处、静止区域等可能出现相同画面，所以输出 60 fps 不表示每秒都有 60 张互不相同的图像。参数语义见 [FFmpeg minterpolate 文档](https://ffmpeg.org/ffmpeg-filters.html#minterpolate)。

原始帧间隔约为 41.67 ms，目标帧间隔约为 16.67 ms。24 到 60 的比率为 2.5，目标采样点需要根据时间落在原帧之间，并非给每张原帧固定插入相同整数张画面。本片的帧数换算正好没有余数：

```text
原片时长 = 5086 / 24 = 211.916666… 秒
目标帧数 = 5086 × 60 / 24 = 12715 帧
输出时长 = 12715 / 60 = 211.916666… 秒
```

### 分段、边界和片尾

本次本地导出分成 11 段：前 10 段各 1200 个目标帧，即 20 秒；最后一段 715 帧。最多同时运行 6 个 FFmpeg 进程，每个进程使用 1 个滤镜线程和 2 个视频编码线程。

每段额外读取边界前后各 2 个原始帧，让运动估计取得邻近画面，再按目标时间范围裁掉多读的内容。片尾通过 `tpad=stop_mode=clone:stop_duration=0.20` 提供短暂的尾帧上下文，最后限制输出帧数。补出的上下文不延长交付视频。

各段编码参数一致，完成后先核对帧数与 60 fps，再按顺序拼接并复制音轨。`-g 120` 设置最大 GOP 为 120 帧，约 2 秒；编码器仍可以在切镜处提前插入关键帧。分段起点也会影响关键帧分布，因此分段编码与整片单进程编码不保证文件大小或视频字节完全相同。

## 2. 为什么 1080p / 60 fps 文件只比 720p 大约 15%

这里比较的是**硬盘上的压缩文件大小**。对于相同时长的视频，可以近似计算：

```text
文件字节数 ≈ 时长 ×（视频平均码率 + 音频平均码率）÷ 8
```

再加上封装开销，并考虑码率统计口径。代入本次实测值：

```text
720p / 24 fps：211.916667 × (3.916109 + 0.323082) ÷ 8 ≈ 112.294 MB
1080p / 60 fps：211.916667 × (4.531097 + 0.323082) ÷ 8 ≈ 128.585 MB
```

计算值与实际的 112.457 MB、128.930 MB 接近。两个文件的平均总码率接近，所以最终文件大小也接近。

### 编码配置同时发生了变化

720p 版采用 CRF 12，60 帧版采用 CRF 18，并加入 VBV 码率约束。同一个编码器下，更高的 CRF 允许更强的有损量化；在复杂段落触及码率约束时，编码器还需要进一步分配有限的比特。因此这组数据体现了分辨率、帧率与压缩配置的共同变化，不能当作相同质量条件下仅改变帧率的实验。

`-maxrate 4500k -bufsize 9000k` 和 `-maxrate 8000k -bufsize 16000k` 分别是两种输出的 VBV 设置。`maxrate` 控制码率约束，`bufsize` 以 **bit** 表示假想码率缓冲容量；它不等于编码进程的 RAM 上限。VBV 允许一定的短时波动，分段初始缓冲和统计口径也会影响实测均值，所以 4.531 Mbps 与设置值 4.5 Mbps 的小幅差别不宜解读成全片大小的精确硬上限。相关选项见 [FFmpeg 编码选项](https://ffmpeg.org/ffmpeg-codecs.html#Codec-Options) 与 [libx264 文档](https://ffmpeg.org/ffmpeg-codecs.html#libx264_002c-libx264rgb)。

### 压缩编码会利用相邻画面的关联

H.264 使用帧间预测，视频文件无需独立存储每一帧的全部像素。对于本项目大量重复的面板、文字布局和连续运动，编码器可以复用参考画面、记录运动与残差。插值产生的邻近画面通常也有较强关联，有利于这种编码；这是对画面结构的解释，不能替代相同配置下的压缩实验。

如果不压缩，1080p / 60 fps 相比 720p / 24 fps 的像素处理量约为：

```text
分辨率比例 × 帧率比例 = (1920×1080)/(1280×720) × 60/24 = 5.625 倍
```

最终压缩文件只增加 14.65%，并不意味着这些额外像素没有成本，也不表示两份成片的压缩损失相同。2K 版实测增加 **88.51%**，它的平均视频码率约 7.667 Mbps，不能归入“体积只大一点”的结论。

## 3. 文件大小与运行时内存有什么关系

播放或渲染时，压缩视频需要还原为像素，再交给滤镜、编码器或显示设备。内存需要容纳当前画面、参考帧、前瞻队列和算法数据，而不只是压缩文件。

对于相同的 8-bit `yuv420p`，忽略行对齐和额外开销，一帧像素数据约为 `宽 × 高 × 1.5` 字节。这里使用二进制 MiB，即 1 MiB = 1,048,576 字节：

| 分辨率 | 单帧 `yuv420p` 数据 | 相比 720p |
|---|---:|---:|
| 1280×720 | 1.318 MiB | 1 倍 |
| 1920×1080 | 2.966 MiB | 2.25 倍 |
| 2560×1440 | 5.273 MiB | 4 倍 |

这张表是**单帧数据量估算**，不是播放器或编码进程的内存测量。本次没有采集峰值 RSS、显存或播放内存，因而不能根据成片大小声称“60 帧版本内存也只增加约 15%”。显示阶段转换成 RGB、硬件解码、参考帧数量和程序实现都会改变实际占用。

流式处理会按需保留一部分帧，不需要把全片 12715 帧同时装进内存。因此帧数增加 2.5 倍也不必然让峰值 RAM 增加 2.5 倍。帧率上升通常增加单位时间内的解码、处理和显示工作；更高分辨率增加每帧的数据量。

本次把运动估计放在 720p 阶段，限制每个进程的线程数，并将已完成的分段写入磁盘。这些做法可以控制流程中的并发和中间数据，但 6 个并发进程各自持有缓冲，仍需计入总内存。若要比较实际内存，应在相同播放器或编码配置下采集整棵进程树的占用，并单独记录硬件解码与显存。

## 4. 用现有项目输出复现后处理

需要 PATH 中的 `ffmpeg`、`ffprobe`，且 FFmpeg 包含 `minterpolate` 与 `libx264`。可以先检查：

```sh
ffmpeg -hide_banner -h filter=minterpolate
ffmpeg -hide_banner -h encoder=libx264
```

这套后处理使用 FFmpeg 的软件滤镜和软件编码器，可用于 Windows、macOS 和 Linux，无须 Apple Silicon 或 CUDA。Windows 构建可从 [FFmpeg 下载页的 Windows 链接](https://ffmpeg.org/download.html#build-windows) 获取；具体构建仍应通过以上命令确认所需功能。

先通过原有构建流程生成 `out/film_master.mp4` 和带配乐的 `out/film.mp4`，并确认歌曲已对齐。下方以母版作为视频输入，以 720p 播放版作为音频输入，直接复制其中已经混好的 AAC；不要求仓库内存在此次本地生成的独立音频文件。

下面均为**整片单进程示例**。时间与帧数适用于本片的 5086 帧、24 fps 母版；其他输入先读取真实帧数与帧率，按 `ceil(原帧数 × 60 / 原帧率)` 计算目标帧数。命令采用 `-n`，输出文件已存在时会停止。请在项目根目录执行，并使用与终端匹配的写法。

### bash / zsh：1080p / 60 fps

```sh
ffmpeg -hide_banner -n -filter_threads 1 \
  -i out/film_master.mp4 -i out/film.mp4 \
  -map 0:v:0 -map 1:a:0 \
  -vf "scale=iw:ih:out_color_matrix=bt709:out_range=tv,format=yuv420p,tpad=stop_mode=clone:stop_duration=0.20,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:mb_size=16:search_param=16:vsbmc=1:scd=fdiff:scd_threshold=5,trim=duration=211.916666666667,setpts=PTS-STARTPTS,scale=1920:1080:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -frames:v 12715 -t 211.916666666667 \
  -c:v libx264 -threads 2 -preset medium -crf 18 \
  -maxrate 4500k -bufsize 9000k -profile:v high -level:v 4.2 -g 120 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -r 60 -fps_mode cfr -c:a copy -movflags +faststart \
  out/film_1080p60_example.mp4
```

### bash / zsh：2K / 60 fps

```sh
ffmpeg -hide_banner -n -filter_threads 1 \
  -i out/film_master.mp4 -i out/film.mp4 \
  -map 0:v:0 -map 1:a:0 \
  -vf "scale=iw:ih:out_color_matrix=bt709:out_range=tv,format=yuv420p,tpad=stop_mode=clone:stop_duration=0.20,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:mb_size=16:search_param=16:vsbmc=1:scd=fdiff:scd_threshold=5,trim=duration=211.916666666667,setpts=PTS-STARTPTS,scale=2560:1440:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -frames:v 12715 -t 211.916666666667 \
  -c:v libx264 -threads 2 -preset medium -crf 18 \
  -maxrate 8000k -bufsize 16000k -profile:v high -level:v 5.1 -g 120 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -r 60 -fps_mode cfr -c:a copy -movflags +faststart \
  out/film_2k60_example.mp4
```

### Windows：PowerShell 5.1 / 7

将 FFmpeg 的 `bin` 目录加入 PATH，在项目根目录打开 PowerShell，先确认能找到工具：

```powershell
Get-Command ffmpeg.exe, ffprobe.exe
ffmpeg.exe -hide_banner -h filter=minterpolate
ffmpeg.exe -hide_banner -h encoder=libx264
```

先选择一组输出设置。导出 1080p / 60 fps 时执行：

```powershell
$pv60Scale = '1920:1080'
$pv60Maxrate = '4500k'
$pv60Bufsize = '9000k'
$pv60Level = '4.2'
$pv60Output = '.\out\film_1080p60_example.mp4'
```

导出 2K / 60 fps 时改用这一组：

```powershell
$pv60Scale = '2560:1440'
$pv60Maxrate = '8000k'
$pv60Bufsize = '16000k'
$pv60Level = '5.1'
$pv60Output = '.\out\film_2k60_example.mp4'
```

选定设置后，执行下面的公共命令。参数用字符串数组逐项传入，路径与滤镜作为完整参数保留；不需要 bash 的反斜杠续行。写法依据 [PowerShell 数组参数展开说明](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_splatting#splatting-with-arrays)。

```powershell
$pv60Filter = 'scale=iw:ih:out_color_matrix=bt709:out_range=tv,format=yuv420p,tpad=stop_mode=clone:stop_duration=0.20,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:mb_size=16:search_param=16:vsbmc=1:scd=fdiff:scd_threshold=5,trim=duration=211.916666666667,setpts=PTS-STARTPTS,scale=' + $pv60Scale + ':flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv420p'
$pv60Args = @(
    '-hide_banner', '-n', '-filter_threads', '1',
    '-i', '.\out\film_master.mp4', '-i', '.\out\film.mp4',
    '-map', '0:v:0', '-map', '1:a:0',
    '-vf', $pv60Filter,
    '-frames:v', '12715', '-t', '211.916666666667',
    '-c:v', 'libx264', '-threads', '2', '-preset', 'medium', '-crf', '18',
    '-maxrate', $pv60Maxrate, '-bufsize', $pv60Bufsize,
    '-profile:v', 'high', '-level:v', $pv60Level, '-g', '120',
    '-colorspace', 'bt709', '-color_primaries', 'bt709',
    '-color_trc', 'bt709', '-color_range', 'tv',
    '-r', '60', '-fps_mode', 'cfr', '-c:a', 'copy', '-movflags', '+faststart',
    $pv60Output
)
ffmpeg.exe @pv60Args
```

Windows 的 CMD 与 PowerShell 使用不同的命令语法；这段数组写法应粘贴到 PowerShell 中。若复制前面的 bash / zsh 命令，应先转换续行和引号写法。终端语法的区别见 [PowerShell 命令解析文档](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing#line-continuation)。

示例同时在 `minterpolate` 中设置 `fps=60`，并在输出端显式设置 `-r 60 -fps_mode cfr`。前者生成 60 fps 的插值时间点，后者固定编码/封装的恒定输出帧率；这样可避免部分 FFmpeg 版本在后续 `trim` / `setpts` 后重新猜测输出帧率。

以上示例使用与实际成片相同的核心滤镜和交付编码配置，但没有本次的 6 路分段调度，不能承诺复现相同文件字节、大小或耗时。`faststart` 调整 MP4 元数据位置以方便播放，不负责降低视频码率。复制音轨要求输入已有可封装到 MP4 的音轨；这里使用原项目播放版的 AAC。

## 5. 核对结果与验证范围

本次成片核对确认：

- 两份 60 帧视频的分辨率分别为 1920×1080 与 2560×1440。
- 标称及平均帧率均为 `60/1`，视频各有 12715 帧，时长均为 211.916667 秒。
- AAC 音轨为 44.1 kHz、双声道，时长与画面匹配。
- 两份 60 帧成片的音频包 SHA-256 均与已对齐的源混音一致，歌曲及提示音没有再次压缩。

可以用下列命令读取输出信息；替换文件名即可核对另一种规格：

```sh
ffprobe -v error \
  -show_entries "format=duration,size:stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_frames,duration,bit_rate,sample_rate,channels" \
  -of json out/film_1080p60.mp4

# 比较以下两行的 SHA-256 值；这里只读取压缩音频包，不解码视频。
ffmpeg -v error -i out/film.mp4 -map 0:a:0 -c copy -f streamhash -hash sha256 -
ffmpeg -v error -i out/film_1080p60.mp4 -map 0:a:0 -c copy -f streamhash -hash sha256 -
```

真实成片的历史导出使用 macOS / Apple Silicon 上的 FFmpeg 9.0.2。2K 本地分段导出日志记录总耗时约 425 秒；这是一次执行记录，不构成不同机器或编码器版本的性能保证。仓库提交不包含这些媒体文件，因此本次文档贡献没有在当前环境重新读取真实成片。

提交前另在 Linux / x86_64、FFmpeg 7.1.5 上用 50 帧、24 fps 的合成视频与独立 AAC 音轨运行两种单进程配置。两份输出分别为 1920×1080 与 2560×1440，均为 60 fps、125 帧，封装时长 2.083333 秒；两份输出中复制的 AAC 包 SHA-256 一致，并与源音轨对应的 2.066009 秒复制包范围一致。该检查只验证命令、时间戳、目标规格和音轨复制，不替代真实 PV 的视觉验收。

PowerShell 示例采用相同的 FFmpeg 参数；两种输出设置展开后与 bash / zsh 示例逐项比对。当前没有 Windows / PowerShell 实机运行记录，Windows 的工具发现、参数传递和完整导出仍需在相应环境确认。

以上是元数据、时长及压缩音频包核对，**没有进行 60 帧成片的抽帧或逐帧视觉验收，也没有测量运行时内存峰值**。快速文字跳变、遮挡、闪烁等可能产生运动估计误差；启用切镜检测可以减轻跨镜头混合，但不能保证所有文字都不变形。原生按 60 fps 重新生成场景与后处理插帧属于不同的制作方式。

相关源码与资料：[项目构建入口](../build.py)、[制作原理](HOW_IT_WORKS.md)、[FFmpeg minterpolate](https://ffmpeg.org/ffmpeg-filters.html#minterpolate)、[FFmpeg 编码选项](https://ffmpeg.org/ffmpeg-codecs.html#Codec-Options)、[FFmpeg 视频选项](https://ffmpeg.org/ffmpeg.html#Video-Options)。
