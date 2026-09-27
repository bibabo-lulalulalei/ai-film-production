---
gate_id: G07
after: "13"
authority: validation/lint_cards.py --gate B
pass_authority: system
zero_cost: true
---

# G07 提示词冻结闸

写好词、**提交付费生成之前**。零费用脚本闸：

```bash
python validation/lint_cards.py <root> --gate B    # 等价 --gate G07
```

脚本只审 **status=locked** 的镜头卡，按其 `<SHOT>.gen.json` 的 `mode` 分派。
**模式判错＝整份词白写**，先过前两项。

## 机器项（结构化数据 ＋ prompt.md 的封闭结构 token）

脚本**不评判任何句子的措辞**，但会从 prompt.md 提取**不用理解内容、零歧义**
的封闭结构 token，与 profile 确定性比对。从根上消除「写对了但被机器误判」，
同时让段数/标签/秒数这类机械错误在花钱前被拦下。

1. **文件就位**：每镜 `08-prompts/<SHOT>.prompt.md` 与 `<SHOT>.gen.json`
   均存在；仅 locked 卡可过闸。
2. **gen.json 结构与枚举**：必填字段齐全（不含已废弃的 core_fields /
   first_line_instruction——出现即 FAIL 并指引删除）；mode 在目标模型 profile
   的 conditions 键内；model/resolution 为 profile 允许值。
3. **参考槽**：ref_images/ref_audios（及 Ref2VA 的 ref_videos）指向的文件
   全部存在；**gen.json 的 label 只能是带尖括号的模板标签**（`<Picture N>`/
   `<Subject N>`/`<Video N>`/`<Audio N>`，正则强卡）；正文里引用标签时通常
   同样带尖括号，但**官方 FL2VA 句式裸写 `Picture N`（无尖括号），闸机两种
   都认**；role 为受控枚举，且 role 与标签类别
   的映射符合 profile `tag_policy.role_tag`；槽位顺序符合 `tag_policy`
   （有父尾帧父尾帧占 ref_image_0、Style Key 紧随；无父尾帧 Style Key 占 0）；
   Picture/Subject/Video/Audio 编号各自从 1 连续；每张定妆 sheet/道具宫格/
   场景图整图占一槽（character-sheet/prop-grid/scene-grid），多格 scene-grid
   行同时注明本镜 cell（single 单图无 cell 位）。
4. **数量上限**：图片按 gen.mode 对应 checkpoint（FL2VA 0–2 张；Ref2VA ≤9），
   视频 ≤3、音频 ≤3、文件总数 ≤12；音频不得作为唯一输入；**FL2VA 双帧占满
   图槽时豁免 Style Key**（无槽可放，风格由正文风格句承担）；开口镜必绑角色
   tts（多镜复用同一 wav）；gen.duration_s＝镜头卡 duration_s。
5. **prompt.md 结构 token**：
   - **段首全等**：段名序列与 profile `core_fields` 全等、按序、各一次
     （基础四模式 3 段；Ref2VA 6 段）；
   - **首行锚点**：按 profile `conditions[mode].first_line` 核对——none 时
     正文直接以第一个字段开头；first_frame 时首行含 `<Picture 1>`＋`0.00`；
     last_frame 时 `<Picture 1>`＋`S.SS`（＝duration，两位小数）；first_last
     时 `<Picture 1>`@0.00 ＋ `<Picture 2>`@S.SS；首行后空一行；
   - **标签双向对账**：正文出现的每个标签都在 gen 声明、gen 声明的每个标签
     正文都有使用。

## 人审（需要判断内容的项，提交前必做）

机器只核结构 token，因此下面这些一条都不能省——打开该模式模板逐行核对：

1. **逐张图核对描述**：prompt 对每张参考图的描述是否＝图里实际内容（目视为准），
   职责与 retention 是否正确。
   - ★ **场景引用句**：多格 scene-grid 参考，正文是否写了
     `the <panel-position> panel of <Subject N> is fully referenced for this shot`；
     panel-position 是否与 gen 的 cell、镜头卡 needs 的 cell 一致。**缺引用句或
     格位不符＝本条不通过**（只给整张宫格、不点名第几格，模型会混格）。
     **single 单图无 panel**：改写
     `the scene image <Subject N> is fully referenced for this shot`。
2. **首行逐字与模式**：模式判对；首行除标签/秒数正确外，**英文措辞为该模式
   逐字句**（结构机器已卡，逐字人审）。
3. **镜头与剪切**：`[Shot N]` 从 1 连续；非首镜 `At MM:SS.mmm` 严格递增、
   不超 duration；cut 用受控动词；dissolve/fade/wipe 仅当用户 explicitly
   requested。
4. **运镜**：在模板词表内；幅度仅 small/large、速度仅 slow/fast，中等/常速
   省略；写成自然动作而非句末堆叠。
5. **对白**：说话人 `(Sx)` 从 1 连续、合说升序、不发声不分配 ID；
   `<d>[Language] 原话</d>` 逐字、以语言标签开头；旁白句后紧跟 lips remain
   completely closed；跨 cut 成对 `<scenetrans>`；片尾截断用 `<cutoff>`。
6. **声场两段**：overall_soundscape 1–4 句不复述对白；non_diegetic_music
   1–3 句只写乐器/速度/节奏/力度、不用抽象情绪词（无音乐写 N/A）。
7. **内容忠实**：正文逐 T 点对应锁定卡 timeline；镜头卡→prompt 无新增/丢失
   剧情；I2VA 首帧描述确为父尾帧内容；FL2VA 豁免 Style Key 时正文风格句
   足以承载风格。
8. **Ref2VA 篇幅**：仅 Ref2VA **生成类任务**——detailed_description 官方
   参考篇幅 normally 350–500 词；对白密集以装下完整对白时间轴为准并注明，
   视频剪辑类随源片复杂度伸缩。基础四模式官方无词数规定，不套用此数字。

## 提交规则
- 任一机器 FAIL 不提交；人审逐条过。先向人讲清「将发哪个 workflow、模式、
  几张图/音、几镜」，**经确认再花钱**。
- 出片后失败按三档：采样→重抽；词→改过人审再提；设计→ECN 回 G05。
