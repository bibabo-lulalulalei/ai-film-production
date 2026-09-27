# 全流程逐步明细

每环标注 **用 → 产 / 闸**。检查项的权威实现：脚本（机器项）与闸文档（人审
项）；字段契约的唯一来源是 [`../schemas/`](../schemas/)，本文件不复制字段
清单。原则与 why 见 [principles.md](principles.md)。

---

## 全环结构化总表

每环含稳定要素：stage_id / title / prerequisites / inputs / activity / outputs /
gates / scripts / failure_loop。子环 `0b/9b/12b` 以子行标注，不重排主编号。
逐环叙述明细见表后各小节。

| 环节 | 前置 | 输入（用） | 产出落点（产） | 闸 | 脚本 | 失败回环 |
|---|---|---|---|---|---|---|
| [0] 小说家 | 用户种子 | 种子/原文 | `01-novel/novel.md`（＋文首魂草稿）、`soul-checks.json` | G01 | — | 文稿打回 novelist |
| [0b] 定魂 | [0] 过 | 魂草稿＋brief | Soul＝confirmed | 用户确认 | — | 未确认不立项，下游不开工 |
| [1] 立项 | [0b] | 过审小说＋魂 | `00-charter/charter.md`（模型写占位） | 用户书面批准 | — | 未批不继续 |
| [2] 风格定向 | [1] 批 | brief＋小说＋魂＋charter＋全部模型证据 | `03-style/`（comps/candidates/matrix/direction/checks）＋charter 回写 | G02 | `tools/search/web_search.py` | 调研/候选/矩阵打回 style-director |
| [3] 编剧 | [2] 过、模型已回写 | 魂＋定向＋小说＋charter | `02-screenplay/screenplay.md` | G03 | — | 打回 screenwriter |
| [4] 世界设计 | [3] 过 | 剧本＋定向（仅 brightness） | `04-world/<SCENE>/{geography,axis_table,brightness}.json` | G05（人审） | — | 与剧本矛盾上报，不擅自圆 |
| [5] 分镜（叙事区） | [3][4] | 剧本＋世界＋定向＋魂 | `05-shots/<SHOT>.json`（design，相机区空） | G04 | — | 叙事/逐秒/空间锚打回 [5] |
| [6] 摄影 | [5] | 魂＋分镜＋世界＋定向 | 镜卡 `cinematography` 区＋`timeline[].camera` | G04 | — | 机位打回 [6]；物理打回 [5]；风格承载不了回 [2] |
| [7] 资产详细设计 | G04 过 | 定向＋needs＋摄影视点＋世界 | `06-bom/asset-specs/<ASSET>.json`（冻结前无 UNSET） | G05 | — | 打回 asset-designer |
| [8] BOM 归并 | G05 过 | 全部镜卡＋asset-specs | `06-bom/bom.json` | — | `scripts/build_bom.py` | spec 缺失/非法报错回 [7] |
| [9] 风格精冻 | [8] | 定向＋定稿镜卡＋设计卡＋BOM | `03-style/style-spec.json`（画风槽位契约）、`style-bible.md`、样板图 6 张（真实项目的人物/道具/场景各 2 件） | 用户人审 | — | 样板图不过重烧 |
| [9b] 资产词派生 | [8][9] | BOM＋spec＋style-checks＋keys | `06-bom/asset-prompts/<ASSET>.md` | — | `scripts/build_asset_prompts.py` | 无（机械派生） |
| [10] 资产生产 | [9][9b] | 生产提示词＋BOM＋style-bible＋keys | `07-assets/`（道具宫格/简单物 single/人物 sheet/场景图包，≤3 镜场景 single/voices/tts） | G06 | — | 不对整张重烧；设计漏派走 ECN 回 [5] |
| [11] 齐套闸 | [10] | BOM＋全部资产＋spec＋keys | 审核回写 BOM＋覆盖率（100%） | G06 | `validation/coverage.py` | 重产 / 漏派 ECN |
| [12] 锁镜 | G06 过 | 设计卡＋已审资产 | 镜卡 design→locked | lock 核验 | `lint_cards.py --gate lock` | 缺件回 [10]/[11] |
| [12b] 分镜文档 | [12] | 全部锁定卡 | `05-shots/storyboard.md` | — | `scripts/build_storyboard.py` | 无（机械派生） |
| [13] 镜头提示词 | [12b] | storyboard＋锁定卡＋keys＋资产＋tts | `08-prompts/<SHOT>.prompt.md`＋`<SHOT>.gen.json` | G07 | — | 打回 prompt-writer |
| [14] 提交生成＋尾帧人审 | G07 过 | prompt＋gen | `09-takes/<SHOT>/`＋尾帧；provenance 回填 | 尾帧人审 | 平台提交 | 重抽 / 改词过 G07 / 改风格→最高级 ECN 回 [2] |

> 失败回环统一按 ECN 三档（[principles.md §13](principles.md)）：
> 采样→重抽；回弹→强化指令垫样板图重出过 G07；设计/风格→回源重算，风格回 [2] 为最高级。

---

## [0] 小说家 Novelist
- **用**：用户种子/原文 + 交付意图
- **产**：`01-novel/novel.md`（完整散文正文，非提纲）＋文首魂草稿；`01-novel/soul-checks.json`；
  `01-novel/brief.md`（小说简要：题材标签＋视觉需求统计＋画风硬约束，给 [2] 用的索引）
- **闸**：[G01-novel](../gates/G01-novel.md)

## [0b] 定魂（用户）
- **用**：文首魂草稿（＋brief 一并过目）
- **产**：Soul = confirmed。未确认，立项之后全部不开工。

## [1] 立项 Project Charter
- **用**：已过审小说 + Soul
- **产**：`00-charter/charter.md`＝平台/画幅/时长/单分集/语言/分级/目标模型/美学档位。
  **画风一栏写「待 [2] 冻结」**；**目标模型写占位「待 [2]」**——模型随风格组合
  锁定，不先于证据；[2] 用户选定后回写。
- **闸**：用户书面批准。

## [2] 风格定向 Style Direction（编剧之前，视觉之魂）
- **用**：brief + novel + Soul + charter 交付约束 + 同类型作品调研 + 全部模型 style_evidence
- **产**：
  1. `comps.md`（同类型作品调研：作品/视觉特征/出处）；
  2. `candidates.md`（自下而上归纳 N≥3，每候选一份具体文字视觉规格，不收集图片）；
  3. `model-matrix.json`（候选 × **全部已登记模型**四档评级/证据/缓解/排名）；
  4. 用户据候选规格＋矩阵选定「风格×模型」→ **回写 charter 锁定模型**；
  5. `style-direction.md` ＋机器规则 `style-checks.json`
- **详见** [crew/style-director.md](../crew/style-director.md)
- **闸**：[G02-style-direction](../gates/G02-style-direction.md)

## [3] 编剧 Screenwriter（朝风格书写）
- **开工前置**：charter 模型栏已由 [2] 回写锁定；未回写不开工。
- **用**：Soul + style-direction + novel + charter
- **产**：`02-screenplay/screenplay.md`：六步判断/场头/台词编号/细腻对照表/
  分集表/待决疑点。外化手法按画风选。
- **闸**：[G03-screenplay](../gates/G03-screenplay.md)

## [4] 世界设计 World Bible
- **用**：screenplay（+style 仅调 brightness）
- **产（按场景）**：`geography.json`、`axis_table.json`（风格中立）；`brightness.json`（服从风格）
- **闸**：G05 **人审**核对：brightness 与风格定向一致、光源客观方位未被
  擅改（脚本不读 04-world 文件，无机器项）。

## [5] 分镜设计 Storyboard（叙事区）
- **用**：screenplay + 世界三件套 + style-direction + Soul
- **产**：`05-shots/<SHOT>.json`（status=design，相机区空）。
  needs 保持精简（asset_id / kind / target_path），外观细节不在此展开。
  字段契约见 [../schemas/shot-card.schema.json](../schemas/shot-card.schema.json)
- **闸**：G05 ｜ [crew/storyboard-artist.md](../crew/storyboard-artist.md)

## [6] 摄影设计 Cinematography（回填同一卡）
- **用**：Soul + 分镜卡 + 世界三件套 + style-direction
- **产**：镜卡 cinematography 区（机位/焦段/景深焦点/构图/布光/运镜/接续），
  服从风格；并校准 timeline 每条的 camera
- **回环**：物理不成立打回 [5]；风格承载不了反向打回 [2]
- **闸**：G04（脚本）＋ G05

## G04 镜头自检闸（脚本零费用）
位于 [6] 之后、[7] 之前。检查项与人审项见
[G04-shot-selfcheck](../gates/G04-shot-selfcheck.md)，权威实现为
`validation/lint_cards.py --gate S`。

## [7] 资产详细设计 Asset Design（每件一份，跨镜复用）★
- **用**：style-direction + 分镜 needs + 摄影视点 + 世界事实
- **产**：`06-bom/asset-specs/<ASSET>.json`，冻结前无 UNSET。人物/道具/场景
  字段契约分别见 [`../schemas/`](../schemas/) 的 character/prop/scene spec；
  写法指引见 [crew/asset-designer.md](../crew/asset-designer.md)

## G05 设计冻结闸（脚本零费用）
位于 [7] 之后、派生 BOM 与投产之前。机器项与人审项见
[G05-design-freeze](../gates/G05-design-freeze.md)，权威实现为
`validation/lint_cards.py --gate A`（含资产设计卡完整、魂/风格符合）。

## [8] BOM 归并（机械派生，读设计卡）
- **用**：全部镜头卡 + asset-specs
- **产**：`06-bom/bom.json`：按 member（target_path）归并、冲突检测，
  每条含 `spec_path`；同一 asset_id 可有多条 member（人物状态 sheet、
  场景多张 grid），member 间依赖记入 depends_on；开口角色派生 voice + tts
- **脚本**：`scripts/build_bom.py`

## [9] 风格精冻 Style Refinement（放量前验证）
- **用**：style-direction + 定稿镜卡 + 资产设计卡 + BOM
- **产**：① `03-style/style-spec.json`——按
  `schemas/style-spec.schema.json` 的固定槽位填写项目画风（唯一结构化事实源，
  烧样板与生产前先过 `--gate SS`）；② `style-bible.md`（人读操作级规则）；
  ③ 样板图 **6 张**（`keys/<MODE>_key.png`）：从真实项目选代表性人物／道具／
  场景**各 2 件**，照设计卡与 style-spec 小批量烧出，用户逐张**人审**。
- 意义：画风槽位与项目解耦（换项目只换槽内取值）；样板即真实资产、也是各类
  首件，验证模型这次稳，才放量。

## [9b] 资产生产提示词派生（机械派生，读设计卡＋BOM）
- **用**：BOM + asset-specs + style-checks（禁词）+ keys
- **产**：`06-bom/asset-prompts/<ASSET>.md`（每资产一份，覆盖其全部
  member）：设计卡字段全部转成生产语言，逐 member（sheet/grid）成段，
  附验收与负向
- **脚本**：`scripts/build_asset_prompts.py`

## [10] 资产生产 Production（物→人→景）
- **用**：资产生产提示词 + BOM + style-bible + keys
- **产**：props 一物一张多视图宫格（简单物 single 单图）；characters/<CHAR>/
  每角色一张 4 格定妆 sheet（状态变体另出）；scenes/ 地点×状态图包，
  ≤3 镜或同一视点的简单场景出 single 单图；voices、tts。
  每类先出首件、对照设计卡/样板图人审再批量
- **重烧规则**：任一 cell 废 → 整张 sheet/grid 重烧，禁止补单格；
  变体垫已批 main
- **详见** [crew/producer.md](../crew/producer.md)

## [11] 齐套闸 Readiness
- **用**：BOM + 全部资产 + asset-specs + keys
- **产**：审核记录回写 BOM ＋ 覆盖率。人审三步并排（成品↔设计卡/样板图；
  定妆 sheet 四格互比；同场景宫格互比）
- **放行**：覆盖率 100% approved、依赖顺序合规。脚本 `validation/coverage.py`；
  人审项见 [G06-readiness](../gates/G06-readiness.md)

## [12] 锁镜 Lock
- **用**：设计卡 + 已审资产
- **产**：`<SHOT>.json` design→locked：引用路径存在且 approved；开口镜 tts
  存在即可（不核时长）；尾帧父镜 locked、父尾帧就位
- **脚本**：`validation/lint_cards.py --gate lock`

## [12b] 文本分镜文档派生（机械派生，读锁定卡）
- **用**：全部锁定镜头卡
- **产**：`05-shots/storyboard.md`（全片一份）：目录（含时长档位）＋
  逐镜 hook/空间锚卡/场景 grid 与 cell/continuity/double-binding/
  逐秒内容（含落幅点）/ASCII 布局。供人通读跨镜连续性，亦为 [13] 渲染简报
- **脚本**：`scripts/build_storyboard.py`

## [13] 镜头提示词 Prompt（装配）
- **用**：storyboard.md ＋锁定卡 + keys + 定妆 sheet/道具宫格/场景宫格
  （注明本镜 cell）＋角色 tts；有父尾帧加父尾帧；外观细节以**资产设计卡**为准
- **动作顺序**：先判模式（通用五分类见 [models/input-conditions.md](models/input-conditions.md)，
  H3 判别细则见 [models/h3/h3.md](models/h3/h3.md)）；**首行类型与标签策略
  由 profile 唯一派生**（conditions[mode].first_line、tag_policy），再按该
  模型官方模板成稿、指派参考槽
- **产**：`08-prompts/<SHOT>.prompt.md` ＋ `<SHOT>.gen.json`（gen 不重复
  手写段名/首行）；剧情只从锁定卡转译
- **详见** [crew/prompt-writer.md](../crew/prompt-writer.md)

## G07 提示词冻结闸（脚本零费用）
位于写好词、提交付费生成之前。机器项分两层：gen.json 的结构/枚举、参考槽
文件/数量/绑定；以及从 prompt.md **提取封闭结构 token**（段首字段名、模板
标签、首行锚点）与 profile 确定性核对。**措辞/词表/句数仍全部人审**。详见
[G07-prompt-freeze](../gates/G07-prompt-freeze.md)，权威实现为
`validation/lint_cards.py --gate B`。

## [14] 提交生成 + 尾帧人审 ★ skill 终点
- **用**：prompt + gen
- **产**：`09-takes/<SHOT>/` takes ＋ `<SHOT>_tail.png`（顺序长出）；审后
  model/seed/task_id 回填 provenance
- **失败三档**：重抽 / 改词过 G07 / 改风格→最高级 ECN 回 [2]
- **交付**：每镜选定 approved 的 mp4 即为全部成片素材。边界见
  [principles.md](principles.md) 的「skill 的边界」。
