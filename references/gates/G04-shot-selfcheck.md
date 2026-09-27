---
gate_id: G04
after: "6"
authority: validation/lint_cards.py --gate S
pass_authority: system
zero_cost: true
---

# G04 镜头自检闸

在 [6] 摄影设计完成后、[7] 资产详细设计**之前**。零费用脚本闸：

```bash
python validation/lint_cards.py <root> --gate S    # 等价 --gate G04
```

镜头的时长、钩子、空间锚、逐秒指令若站不住，不必浪费功夫写资产设计卡，所以
本闸先于 G05。

## 机器六项（权威实现为脚本）

1. **钩子密度**：hook_type 出自受控词表；任意连续三镜至少一镜
   reveal/reversal/callback；开场镜与收尾镜带强钩。
2. **时长档位**：duration_tier 选 standard（8–12）/motion（12–15）/
   dialogue（4–10）；duration_s 落档内（区间再与 profile 包络相交），超档拆镜。
3. **单镜角色数**：在镜重要角色 ≤ 3。
4. **场景与空间锚**：scene need 绑 grid_id＋cell（一镜一格；single 场景绑唯一格）；地标画面相位、
   主光基线与所绑场景状态一致、跨镜变化时 continuity 显式标注；卡内四子字段
   结构完整，cast_positions 覆盖全部在镜角色。
5. **逐秒覆盖**：timeline 0s→duration 每秒一条无缝隙，每条五元素
   picture/action/camera/sound/handoff，无声写 silent。
6. **跨镜连续**：消失角色进 exited_characters（至少追踪一镜）；handoff 逐条
   非空。

## 人审（机器过后）
- 逐秒指令是否可直接据以生成画面：动作是否具体、弹性拍是否真有挤压拉伸的设计。
- 钩子分布的观感：节奏是否成立（机器只数类型，不判好坏）。
- 机位与空间锚是否符合所绑 cell 的视点与世界设计方位。

## 退回规则
- 叙事/逐秒动作/空间锚 → [5] 分镜；机位/每秒相机/光位 → [6] 摄影。
- 仅修单卡时下游重算，不回 [0]。**不得带 FAIL 进入 [7]。**
