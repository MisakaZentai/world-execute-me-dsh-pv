# input/：你自己准备的东西

歌曲和歌词受版权保护，不在本仓库里。构建前，把它们放到这个文件夹。

## song.mp3（必需）

Mili 的《world.execute(me);》完整音频。

这支片子按下面这个文件逐帧对齐，时间零点就是它解码出来的第一个采样。`data/song.json` 里有同样的数字：

| 项目 | 值 |
|---|---|
| sha256 | `79c4e53663c7966b7160bff19326e614658485d4ce0199ff82715ea9d0a418fc` |
| 时长 | 211.913 s |
| 格式 | MP3，320 kbps，44.1 kHz，立体声 |

- 你的文件和这个不一样也能出片，`python build.py check` 会提示。
- 片头如果多出或少掉一段静音，唱词和镜头会整体提前或推后。可以用 ffmpeg 裁掉或补上静音，让两份的起唱点对齐。

## lyrics.lrc（可选）

- 没有这个文件时，`python build.py lyrics` 会从 LRCLIB（https://lrclib.net ，条目 36914646）下载同步歌词，保存到这里。
- 也可以放你自己的 LRC。它要和那个版本一行一行对应；合成时逐行校验，对不上的地方会明确报出来。
- 歌词只用来在你的本机生成两份文件：`film/world_execute_word_timing_20260927/word_timeline.json` 和 `film/ai_mascot_mv_world_execute_20260926/audio/lyrics_synced.lrc`。它们都在 `.gitignore` 里，不会被提交。
