---
name: ai-film-production
description: >-
  End-to-end, quality-gated pipeline for turning a story idea into finished
  AI-generated video, film, or short-drama assets: novel and brief, style
  direction grown from real reference research and a cross-model capability
  matrix, screenplay, world and shot design, cinematography, per-asset design
  cards, BOM, Style Key plates, asset production, readiness and card lock,
  generative prompts, and rendered shots with tail-frame continuity.
  Model-agnostic; model differences live under references/models, with
  MiniMax H3 as the default profile. Use this skill whenever the user wants
  to plan, set up, or run an AI video/film/短剧 production; choose or freeze
  an art style; design detailed character, prop, or scene assets; design
  shots or generative prompts for video models such as MiniMax H3; manage a
  shot list, BOM, 物料齐套, or asset readiness; or run a structured AI
  filmmaking workflow — even when they only ask for a single stage.
  当用户提到 AI 视频、AI 电影、短剧、画风/美术风格、人物/道具/场景设定、
  分镜、镜头卡、物料/BOM、提示词、出片或跑 H3 时都应使用。
---

# AI Film Production（通用 AI 视频生产流水线）

把一个故事做成 AI 成片素材的完整流水线。它是**项目无关、模型无关的生产
方法**：任何题材、画风、生成模型都套用同一套契约；模型差异隔离在
[`references/models/`](references/models/) 内（默认 profile 为 MiniMax H3）。

## 翻车 → 根治原则

| 真实翻车 | 根治原则 |
|---|---|
| 各环节各自补事实，画面与参考图、与故事脱节 | **单一事实源**：镜头卡与资产设计卡是仅有的手写源；BOM、状态、提示词全部机械派生。有错回源文件改、下游重算 |
| 画风拍脑袋、模型先于证据锁定，之后全片漂移 | **画风两层制**：编剧前据小说简要调研同类型作品、自下而上给 N 个具体视觉规格的候选（不收集参考图片），再对全部已登记模型出能力矩阵，由人锁定「风格×模型」；放量前再用《样板图》做风格级首件验证 |
| 资产规格太薄，模型逐件自由发挥走样 | **每件一份《资产设计卡》**：字段填全才准冻结、投产 |
| 分区越界，下游改上游的东西 | **字段分区**：分镜不碰相机字段；摄影不改剧情；资产只细化外观；生产不改设计；写词不新增情节 |
| 空着让下游猜、或未审先投 | **锁 / 填 / 投**：锁定后不可变；信息不足写 `UNSET` 登记待补，绝不臆造；只投递已锁定 ID、路径、垫图 |
| 画风名存实亡 | **画风＝视觉之魂**：风格定向冻结后全链围绕；改风格＝最高级 ECN，没有「只改一处」 |

另有两条不变前提：**尾帧内容只能顺序长出**（路径可预制、内容不可预制）；
**编号一经引用不重排**。母题（魂）常驻全链——镜头卡有可追溯标记，每道闸含
「魂/风格符合」行：可计算项脚本查，意味气质留人审。付费生成前先讲清将做
什么、依据什么，经确认再花钱。

完整原则与原因见 [`references/principles.md`](references/principles.md)。

## 标准工程结构（Canonical Layout）

```
<project-root>/
├── 00-charter/charter.md                立项：交付规格 + 美学档位；目标模型先写「待[2]」，选定后回写（不含画风）
├── 01-novel/novel.md                    完整小说正文（文首「魂」块）
│   ├── brief.md                         小说简要（题材标签/视觉统计/画风硬约束）
│   └── soul-checks.json                 魂的机器规则
├── 02-screenplay/screenplay.md          朝风格定向书写的分场剧本
├── 03-style/                            ★画风工序（两层都在此目录）
│   ├── comps.md                         同类型作品调研（视觉特征/出处）
│   ├── candidates.md                    N 个自下而上归纳的候选（具体文字视觉规格）
│   ├── probes/                          小探针渲染（事先确认后归档）
│   ├── model-matrix.json                候选 × 全部模型的能力矩阵
│   ├── style-direction.md               冻结的风格定向（视觉之魂·粗）
│   ├── style-spec.json                  ★画风规格（槽位契约·画风唯一结构化事实源）
│   ├── style-bible.md                   风格精冻（人读操作级规则）
│   ├── style-checks.json                风格机器规则（禁词/必引样板图/色锚）
│   └── keys/<MODE>_key.png              样板图
├── 04-world/<SCENE>/                    世界设计（纯事实 JSON）
│        ├── geography.json               方位（风格中立）
│        ├── axis_table.json              轴线（风格中立）
│        └── brightness.json              光序（服从风格）
├── 05-shots/<SHOT>.json                 镜头卡（design→locked）
│   └── storyboard.md                    [12b] 派生的全片文本分镜
├── 06-bom/
│   ├── asset-specs/<ASSET>.json         ★资产设计卡（每件一份，跨镜复用）
│   ├── asset-prompts/<ASSET>.md         由设计卡生成的生产提示词
│   └── bom.json                         物料总名单（脚本派生，按 member 归并）
├── 07-assets/                           照设计卡生产，烧进预制路径
│   ├── props/<PROP>.png                 一物一张多视图宫格（简单物单图）
│   ├── scenes/<SCENE>_<grid_id>.png     地点×状态的图包（≤3镜 single 单图；4 视点起宫格）
│   ├── characters/<CHAR>/<CHAR>_sheet.png   一张 1×4 横向定妆条（状态变体另出）
│   ├── voices/<CHAR>_voice.wav          原始嗓音，仅供克隆，不喂模型
│   └── tts/<CHAR>_tts.wav              每角色一个声音参考，开口镜共用
├── 08-prompts/<SHOT>.prompt.md          镜头生成提示词
│           └── <SHOT>.gen.json          生成参数 + 绑定 + provenance
└── 09-takes/<SHOT>/<SHOT>_tail.png      takes 与尾帧（内容只能顺序生成）
```

> 片子专名、形制、可读文字只写在**项目根**，绝不写回本 skill 的 `references/`。

## 流水线一览（编号即步骤）

```
[0] 小说家        种子/原文              → 小说正文 + 魂草稿 + 小说简要
[0b] 定魂(用户)   魂草稿(+brief过目)     → Soul confirmed
[1] 立项          小说 + Soul            → charter：交付规格 + 美学档位；模型写「待[2]」
[2] 风格定向 ★   brief+小说+魂+交付约束 → 同类调研 → N带图候选 → 跨模型矩阵
                                                          → 用户选定组合 → 回写charter → 风格定向
[3] 编剧          Soul + 风格定向         → 朝风格书写的分场剧本（charter已锁模型）
[4] 世界设计      剧本 (+风格调brightness)→ 方位/轴线中立，brightness 服从风格
[5] 分镜设计      剧本+世界+风格+魂       → 镜头卡叙事区＋逐秒 timeline（相机区空）
[6] 摄影设计      Soul+分镜+世界+风格      → 回填摄影基线与每秒相机变化
── G04 镜头自检闸（脚本，零费用）───────────────────────────
[7] 资产详细设计 ★ 风格+分镜+摄影+世界   → 每件一份资产设计卡（字段填全）
── G05 设计冻结闸（脚本，零费用）───────────────────────────
[8] BOM 归并      全部冻结卡 + 设计卡      → BOM：按 member 归并/冲突/voice+tts
[9] 风格精冻 ★   风格定向+定稿+设计卡+BOM → 风格经 + 样板图（小批量+人审）
[9b] 资产词派生   BOM + 设计卡 + 禁词      → 06-bom/asset-prompts/（逐 member）
[10] 资产生产     生产提示词+样板图         → 物（宫格）→人（定妆 sheet）→景（宫格包）
[11] 齐套闸       BOM+资产+设计卡+样板图   → 三步并排人审 + 覆盖率 100%
[12] 锁镜         设计卡+已审资产          → design→locked
[12b] 分镜文档    锁定卡                  → 05-shots/storyboard.md（double-binding + ASCII）
[13] 镜头提示词   分镜文档+样板图+member资产 → 先判模式，按官方模板写 prompt + gen
── G07 提示词冻结闸（脚本，零费用）────────────────────────
[14] 提交生成 ★  prompt + gen           → takes/尾帧人审 → 成片素材（skill 终点）
        ↑ 失败三档：重抽 / 改词过G07 / 改风格→最高级ECN回[2]

  组接 / BGM / 混音 / 字幕：不在 skill 内，用户自行在剪映完成
```

## 入口路由（按用户现状进入，勿从头重跑）

| 用户现状 / 说法 | 先做什么 | 跳到 |
|---|---|---|
| 新故事 / 给主题种子 | 读 [`references/crew/novelist.md`](references/crew/novelist.md) | [0] |
| 已有小说，要立项 | 核小说过 G01 + 魂确认 | [1] |
| 「定画风 / 选美术风格」 | 立项后据 brief 做同类调研、候选与跨模型矩阵 | [2] |
| 已有风格定向，要剧本 | 核风格已冻结 | [3] |
| 已有剧本，要分镜 | 先核世界设计 | [4][5] |
| 分镜好了，要摄影 | 读 cinematographer 回填 | [6] |
| 摄影完成、要细化资产 | 先跑镜头自检 | G04 |
| 「细化人物/道具/场景设定」 | G04 过 → 写资产设计卡 | [7] |
| 「设计冻结 / 能不能做」 | 跑 G05 | G05 |
| 「造物料 / 出资产」 | G05 过 → BOM → 风格精冻 → 派生生产提示词 → 生产 | [8–10] |
| 「写 H3/模型词」 | 锁镜后装配 prompt + gen | [13] |
| 「渲染 / 跑片」 | G07 过 → 提交 → 尾帧人审 | [14] |
| 只改一镜 | 只动该卡，下游重算，勿回 [0] | ECN |
| 缺文件却要下游 | **停**，一次性列出缺的代号 | — |

## 脚本与工具（在 skill 根执行）

**派生脚本**（机械产出，仅用 Python 标准库）：

```bash
python scripts/build_bom.py  <root>              # 派生 BOM：按 member 归并/冲突（读设计卡）
python scripts/build_asset_prompts.py <root>     # [9b] 派生资产生产提示词（逐 member）
python scripts/build_storyboard.py <root>        # [12b] 派生全片文本分镜文档（读锁定卡）
python scripts/build_axis.py <root>              # [4] 方位脚本：facing→左右映射（禁心算）
python scripts/produce_asset.py <root> --id <A>  # [10] BOM 驱动投产（默认 dry-run；--submit 经后端适配器真出图）
python scripts/mark_review.py <root> --path <p> --status produced|approved|rejected  # 审态唯一写入器（approved 须 --by 用户）
python scripts/freeze_prompt.py <root> --shot <SHOT>   # 冻结：prompt/gen/参考件 sha256 指纹
python scripts/submit_take.py   <root> --shot <SHOT> [--confirm]  # [14] 凭冻结提交；付费前打印清单，--confirm 当场确认
```

> **投产约束**：[10] 不再用手写一次性批次——produce_asset 按 BOM pending 行取生产词、
> 真垫 Style Key、烧进预制 target_path，成功回写 produced；审批由用户经 mark_review
> `--by` 标记，脚本不自批。真实出图的后端差异在 `scripts/image_backends/` 适配器内。

**校验闸**（只查结构化数据，不读提示词正文/图片内容）：

```bash
python validation/lint_cards.py <root> --gate SD    # G02：风格定向/候选/矩阵/模型回写（镜卡产生之前）
python validation/lint_cards.py <root> --gate SS    # 画风规格槽位契约（[9] 烧样板前，fail-loud）
python validation/lint_cards.py <root> --gate W     # [4] 世界完整性：三件套存在/过 schema/引用一致，过则 frozen
python validation/lint_cards.py <root> --gate S     # G04：钩子/时长/空间锚/逐秒自检
python validation/lint_cards.py <root> --gate A     # G05：魂/风格符合 + 设计卡字段完整
python validation/lint_cards.py <root> --gate lock [--shot <SHOT>]  # 锁镜；--shot 单镜核验（尾帧链交错）
python validation/lint_cards.py <root> --gate B     # G07：gen 结构/枚举/参考槽
python validation/lint_cards.py <root> --gate T [--shot <SHOT>]  # take 交付：approved take/尾帧/provenance
python validation/coverage.py    <root>             # 齐套覆盖率（须 100%）
python validation/check_manifest.py                 # OM：产出物价值总账（V3 必有机械消费；删除须理由）
```

> **产出物总账**（[`outputs-manifest.data.json`](outputs-manifest.data.json)，契约见
> [`schemas/outputs-manifest.json`](schemas/outputs-manifest.json)）：登记每个标准产出物的
> 价值级别（V3/V2/V1）与处置（补下游/人审留痕/合并单源/条件/归档/删除）。OM 闸强制：
> **高价值产出物必须有机械消费者，删除必须附"无独立价值"证据**——防止字段被静默删掉。

**实用工具**（按需，配置与依赖见 [`tools/README.md`](tools/README.md)）：

```bash
python tools/s3/upload.py <path-or-url>             # 上传 S3 拿 CDN URL（H3 参考需 URL）
python tools/video/ffmpeg_tool.py frame <v> <o> --tail  # 抽尾帧（尾帧链）
python tools/search/web_search.py "<query>"         # 联网文本调研（需凭证）
```

Windows 乱码时设 `PYTHONIOENCODING=utf-8`。校验只查**引用/字段/契约/机器项**
（ID、路径、已审、槽位、样板图、禁词、色锚、设计卡必填字段、魂机器项）；
G07 还会从 prompt.md **提取封闭结构 token**（段首字段名、模板标签、首行锚点）
与 profile 做确定性核对——但不评判任何句子的措辞；**查不了图片内容、视角与
味道**——逐张开图人审的职责不可省略。所有模型相关数值以目标模型 profile 为准。

## 去哪里查

- 全流程逐步明细（每环引用物/产出物/闸）：[`references/pipeline.md`](references/pipeline.md)
- 单一事实源、画风两层、资产设计卡、魂、样板图、ECN 的 why：[`references/principles.md`](references/principles.md)
- 资产生产提示词模板（人物/道具/场景三份，生图模型无关）：[`references/asset-prompt-templates/`](references/asset-prompt-templates/)
- 各岗位职责：[`references/crew/`](references/crew/)
- 各道闸（人审项与机器项）：[`references/gates/`](references/gates/)
- 模型选择与新模型适配：[`references/models/README.md`](references/models/README.md)
- 按需实用工具（S3 上传/抽帧/看图/搜索）：[`tools/README.md`](tools/README.md)
- 镜头卡 / BOM / 资产设计卡 / profile 契约：[`schemas/`](schemas/)；各契约填好的样例见 [`schemas/examples/`](schemas/examples/)
