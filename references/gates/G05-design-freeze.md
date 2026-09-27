---
gate_id: G05
after: "7"
authority: validation/lint_cards.py --gate A
pass_authority: system
zero_cost: true
---

# G05 设计冻结闸

在分镜叙事区与摄影区都完成后、派生 BOM 与投产**之前**。零费用脚本闸：

```bash
python validation/lint_cards.py <root> --gate A    # 等价 --gate G05
```

## 机器项（权威实现为脚本，数值以目标模型 profile 为准）

- **资产设计卡完整 ★**：needs 引用的每件资产均有 spec、必填字段填实、无
  UNSET。人物 sheets（一张 main＋状态变体；固定 4 格）、道具
  presentation.grid（single 或 tl/tr/bl/br）、场景 grids/cells（≤3 镜或
  同一视点可 single 单图；其余 cells 数与 position 匹配 layout；serves_shots
  每镜恰好绑定一格）均过契约检查。
- **模型契约**：参考图/音频数量不超 profile 上限；时长档位/分辨率/
  必填媒体合法；依赖图（含尾帧链、member 依赖）无环、无悬空父镜。
- **模型能力**：逐秒指令对照模型能力审计（一镜内不可生成的变化数、超时长
  动作、做不到的视角）；机位朝向须对得上所绑 cell 的视点（对着 geography /
  axis_table 核，不心算；脚本不读 04-world）。
- **needs 细节**：三件齐 asset_id/kind/target_path，scene 条带 grid_id/cell；
  外观细节不写在镜头卡；同 asset_id 跨镜 kind/target_path 一致
  （同地不同时辰/天气是不同 asset_id）。
- **摄影完整**：cinematography 各字段全部填实、无 UNSET/空占位（脚本只核
  已填，焦段数值合理性人审）。
- **魂覆盖**：按 soul-checks.json 核 motif 次数/顺序/方位，每卡有
  soul.motif_marks。
- **风格符合**：style-checks 的禁词（机器查）；brightness 与风格定向一致
  在人审核。
- G04 的六项结构本闸确认依然成立。

## 人审（机器过后）
- **世界三件套**：逐「场景状态」打开 `04-world/<SCENE>/`，核 brightness
  与该状态及 style-direction 一致、geography/axis_table 的客观方位跨状态
  未被擅改；机位与空间锚对得上所绑 cell 的世界方位（脚本不读这些文件，
  全部人核）。
- 戏眼镜与特殊镜：摄影设计的气质是否衬魂（机器只核字段，不判好坏）。
- 确认本批设计可以投产。

FAIL 按归属退回：剧情/needs→分镜，机位/镜头/布光→摄影，方位→世界设计。
**不得带 FAIL 进 BOM。**
