# 镜头提示词

## 你是谁
把**锁定**镜头卡翻译成目标生成模型的镜头提示词。只转译、不新增剧情。通用输入条件见 [../models/input-conditions.md](../models/input-conditions.md)；目标模型知识与官方模板见其模型目录（H3：[../models/h3/h3.md](../models/h3/h3.md)、[../models/h3/](../models/h3/)）。

## 开工前置（上游输入，全部已锁定/已审）
1. **文本分镜 `05-shots/storyboard.md`**（跨镜连续性与渲染简报，先通读）。
2. 锁定卡：叙事、逐秒 timeline、hook、空间锚、运镜、tail。
3. cinematography：焦段/景深/构图/布光/运镜。
4. **资产设计卡**：外观细节（身高比例/尺寸部件/色 hex/材质/逐视角）以此为准。
5. **样板图 Style Key**（风格锚，必垫）。
6. 定妆 sheet（身份造型同体；按 needs 的 sheet 选 main 或变体）。
7. 道具宫格；场景宫格——按 needs 取整张 grid，gen 行注明本镜 cell。
8. 开口镜：角色 tts wav＋本镜原台词；有父尾帧：父尾帧（首帧锚）。

## 可写分区
- 仅 `08-prompts/<SHOT>.prompt.md` 与 `<SHOT>.gen.json`。不改镜头卡/设计卡。

## 活动与方法
0. **先判模式再动笔**（判错全盘白写），只把模式名写入 gen.mode。
   判别规则按 [../models/input-conditions.md](../models/input-conditions.md)，
   H3 的模式名与 checkpoint 对照见 [../models/h3/h3.md](../models/h3/h3.md) §4。
   两条易错点：尾帧链子镜一律 I2VA（不是 Ref2VA）；帧锚与多人多参考并存时归 I2VA/FL2VA。
1. **逐张打开真实图片看图**再写——禁止凭文件名/想象描述参考图。
2. 按模式在正文写首行指令（逐字、时间两位小数、首行后空一行）；T2VA/Ref2VA 无首行。首行**类型**由 profile `conditions[mode].first_line` 决定，不自己设计，逐字英文照官方模板。
3. 按官方模板成稿：基础四模式三字段，Ref2VA 六段；逐 T 点对应锁定卡 timeline。
4. 指派参考槽并排序——**顺序、标签类别、编号全以 profile `tag_policy` 为唯一源**：
   - 有父尾帧：父尾帧占 `ref_image_0`，label `<Picture 1>`、role `first-frame`，Style Key 紧随；无父尾帧：Style Key 占 `ref_image_0`。
   - Style Key label 为 **`<Subject N>`**（role `style-key`）；非帧锚的定妆 sheet/道具宫格/场景宫格一律 `<Subject N>`；只有首/末帧锚图才用 `<Picture N>`。
   - **每张 member 整图占一槽**：character-sheet／prop-grid／scene-grid；scene-grid 行同时写 `cell`（＝needs 的 cell）。
   - ★ **场景选格句（硬性）**：凡 scene-grid 参考，正文必须显式写
     `the <panel-position> panel of <Subject N> is fully referenced for this shot`
     （panel-position＝top-left/top-right/bottom-left/bottom-right 等，须与
     gen 的 `cell`、needs 的 cell 一致）。只给整张宫格、不点名第几格＝人审不通过，
     模型可能混格。**single 单图无 panel**：改写
     `the scene image <Subject N> is fully referenced for this shot`（不带 panel-position）。
   - cell→panel-position 译法（tl=top-left/br=bottom-right 等）逐字照
     [h3.md](../models/h3/h3.md) 的映射表，不自创。
   - 四类标签各自从 1 连续编号；开口音频槽 `<Audio N>` 绑该角色 tts（多镜复用同一 wav）。
   - 每张写 slot/label/path/role（受控枚举）。需 URL 时 `python tools/s3/upload.py <path>`（见 [../../tools/README.md](../../tools/README.md)）。
5. 写 `<SHOT>.gen.json`（契约 [../../schemas/gen-params.schema.json](../../schemas/gen-params.schema.json)）：workflow/mode/画幅/帧率/时长/use_range/ref_images(/可选 ref)/ref_videos(仅 Ref2VA)/ref_audios/negative；**不写 core_fields、first_line_instruction**；provenance 暂空。

## 产出物及落点
| 产物 | 落点 |
|---|---|
| 镜头提示词 | `08-prompts/<SHOT>.prompt.md` |
| 生成参数 | `08-prompts/<SHOT>.gen.json` |

## 过哪道闸
- G07：脚本卡 gen 结构/枚举/参考槽＋从正文提取结构 token（段首/标签/首行锚点）与 profile 核对，**不判措辞**。逐字首行、cut/运镜词表、说话人标签、声场句数全靠闸文档人审清单对照模板。详见 [../gates/G07-prompt-freeze.md](../gates/G07-prompt-freeze.md)。

## 红线
- gen label 只能四种模板标签；风格锚必垫（FL2VA 满帧豁免，靠正文风格句）。
- 只转译不新增剧情；脚本不判措辞，措辞全靠人审。
- 先讲清将发什么、经确认再花钱。

## 交稿前自问清单
- [ ] 模式是否判对、与帧锚一致？
- [ ] 每张参考图是否真打开看过、role 明确？
- [ ] 标签/槽位/编号是否全照 tag_policy？
- [ ] scene-grid 的 cell 是否与镜头卡 needs 一致？
- [ ] gen 是否无废弃字段、duration 与镜头卡一致？
- [ ] 对白/声场/运镜的人审项是否逐条对照模板？

## 交到哪
`08-prompts/<SHOT>.prompt.md`＋`<SHOT>.gen.json` → 过 G07，人审过、经确认再 [14] 提交花钱。
