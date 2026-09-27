# H3 模型分支

MiniMax H3 的全部资源，同模型不分散。

| 文件 | 性质 | 说明 |
|---|---|---|
| [`profile.json`](profile.json) | 机器读 | 能力档案：4–15s、24fps、32kHz 立体声、两个 checkpoint（FL2VA 图 0–2；Ref2VA ≤9 图/≤3 视频/≤3 音频/总文件 12）、当前封装（AutoDL 仅 768P）、五条件模板映射、标签策略 tag_policy、画风证据库 style_evidence。契约见 [../../../schemas/model-profile.schema.json](../../../schemas/model-profile.schema.json) |
| [`h3.md`](h3.md) | 人读 | 调用契约（AutoDL ComfyUI）、★五模式判别、音频口径、尾帧链、已知坑 |
| [`base-en.txt`](base-en.txt) | 官方模板 | T2VA / I2VA / FL2VA / L2VA 适用，逐字副本 |
| [`ref2va-en.txt`](ref2va-en.txt) | 官方模板 | Ref2VA 六段式，逐字副本 |

## 模板收录说明

两份 txt 为 MiniMax 官方 `h3-prompt-writing` skill 参考模板的**逐字副本**，
收录以保证离线可移植；写词时严格照其字段名、段序、标签与时间格式，不手工
修改。官方模板更新后，直接覆盖文件并 diff。

- 收录日期：2026-09-23；收录时与 MiniMax H3 官方开源仓库及本机
  `h3-prompt-writing` skill 中的副本核对一致（具体核对机路径不写入本 skill）。
- 模板规则如何与镜头卡、gen.json、G07 闸对应，见 [h3.md](h3.md)。
