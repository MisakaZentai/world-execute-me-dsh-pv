# 素材授权来源与核实范围

核实日期：2026-09-30。本页记录事实和证据边界，不替代各许可全文。

## 鲸鱼娘美术

1. 原角色：上善无形 / 上善。署名和许可链见下游保留的 NOTICE；[原作者授权动态](https://www.bilibili.com/opus/1231977657712771073)是进一步核对入口。本次未能实时读取该 B 站动态，不把下游引用写成已实时核验原帖。
2. 女仆二次设计：ZipZipPipe。[Pixiv《AI娘化》](https://www.pixiv.net/artworks/148186519)，作者 ID `18604994`、作品 ID `148186519`。本次通过 [Pixiv 公开接口](https://www.pixiv.net/ajax/illust/148186519)实时核实作者与说明：允许取用，要求标注作者、非商业使用；其中 DeepSeek 娘基于上善鲸鱼娘，遵循 CC BY-NC-SA 4.0。其他角色不能直接套用这项 CC 声明。
3. 立绘：Small-tailqwq / [dsh-deep-whale 的 maid-atelier](https://github.com/Small-tailqwq/dsh-deep-whale/tree/main/maid-atelier)，按上游美术许可链使用。
4. 表情：JAdpp / [dsh-whale-galgame NOTICE](https://github.com/JAdpp/dsh-whale-galgame/blob/main/NOTICE.md)，列明立绘来源与八种新增表情的改编关系。

本仓库保留署名链和上游 NOTICE，许可全文在 `LICENSES/CC-BY-NC-SA-4.0.txt`。改动包括裁切、缩放、调色、像素化、合成、替身摆动及字符网格；只对相应改编部分沿用该许可。上游许可声明不构成对全部潜在第三方权利的保证。

## 音乐与歌词

[Mili Copyright Guidelines](https://projectmili.com/copyright-guidelines)允许个人非商业二创；商业用途按指引另行确认。对全部或部分使用 AI 的同人内容，指引要求明确标注。不得暗示官方作品或官方认可。

原曲和完整歌词不随仓库分发。LRCLIB 下载接口的可访问性不等于音乐或歌词的开源授权。短前缀和连续五词扫描只是打包实现与内容检查，不是法律阈值。

## 原片的 MMD 参考链

原片曾使用 YYB 伯爵女仆模型及动作 01（ドーナツホール，あひるP，编舞足太ぺんた）、02（ハッピーシンセサイザ，ろみ，编舞めろちん）作为参考，再生成舞者画面。

- 模型整包说明包含禁止改造、二配及商业使用等限制；部件的宽松条款不能覆盖整模条款。
- 动作 01 有非商业、使用内容限制、改编与再分发条件；动作 02 允许修改和再分发，并要求合理使用。
- **OPEN QUESTION**：这些现存说明没有明确覆盖 AI 推理参考及其衍生视频。本项目未取得可证明覆盖此用途的补充授权；也不把“没有明确提及 AI”直接解释为禁止。

这些模型、动作、参考视频和生成舞蹈缓存均不在仓库内。默认构建使用立绘替身，原片权限问题仍独立保留。发布原舞者版本前应核清相关条款；无需把第三方模型或动作下载到本仓库才能构建。

## 软件和字体

- dsh 前端及所用 client-ui 样式：DeepSeek，MIT；保留包版本、LICENSE 和来源说明。
- 前端 bundle 内 React / JSX runtime / React DOM / scheduler：保留原标头，附 `LICENSES/React-MIT.txt`。
- Space Mono 与 Anton：随字体保留 OFL；Windows 系统字体不分发。
- 品牌名称和商标不因代码、美术许可而授予额外权利。
