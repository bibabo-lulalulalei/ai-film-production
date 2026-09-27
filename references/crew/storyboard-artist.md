# 分镜

## 你是谁
把剧本切成镜头，产出全链手写事实源之一 `05-shots/<SHOT>.json`。先填叙事区与逐秒骨架，**cinematography 区留空**。规格按风格定向写。

## 开工前置（上游输入，缺一停）
- `screenplay.md`：按动作行切，不按情绪词空想。
- 世界三件套：方位/左右/光直接引用。
- `style-direction.md`：材质/色/线法/肤色体积分寸、异象语法以此为准。
- Soul：本镜承载哪个母题、第几次。

## 可写分区
- 仅镜头卡叙事区（duration_s/hook/timeline/cast/spatial_anchors/needs/soul）。
- cinematography 区由摄影 [6] 回填，本岗留空；不写资产设计卡。

## 活动与方法
字段契约以 [../../schemas/shot-card.schema.json](../../schemas/shot-card.schema.json) 为唯一来源。容易写薄的点：
- **duration_s / duration_tier / hook**：按节拍选档（standard 8–12／motion 12–15／dialogue 4–10），duration_s 落档内，装不下就拆镜；hook_type 用受控词表，别镜镜 setup。档位初填后由摄影 [6] 确认。
- **timeline 逐秒指令**：0s 起每秒一条直到 duration_s、无缝隙（允许 2.0/2.5 子秒拍）；每条五元素 picture/action/camera/sound/handoff，无声写 silent；弹性拍标 squash/stretch/anticipation/overshoot/follow-through。camera 此时只写动作需要的镜头意图，摄影基线留 [6]。
- **cast**：一人一个 character_id＋retention；仅在表演有明确要求时加 required_expression（对应设计卡 expression_list）。
- **spatial_anchors 空间锚卡**：fixed_landmarks / cast_positions（覆盖全部在镜角色）/ exited_characters（上镜在本镜不在者，至少追踪一镜）/ lighting_baseline（与所绑场景状态一致），四子字段都给结构。
- **needs[] 保持精简**：每条 asset_id / kind / target_path；scene 条加 grid_id 与 cell（一镜一格；single 单图场景绑其唯一 single 格），character 条可选 sheet。外观细节（身高/比例/形制/色/材质）不写镜头卡，由 [7] 资产设计卡承载。

## 产出物及落点
| 产物 | 落点 |
|---|---|
| 镜头卡（status=design，相机区空） | `05-shots/<SHOT>.json` |

## 过哪道闸
- G04（与摄影共同，[6] 完成后跑）：叙事/逐秒/空间锚的机器项与观感。详见 [../gates/G04-shot-selfcheck.md](../gates/G04-shot-selfcheck.md)。

## 红线
- 不复制定妆 sheet 内容（member 由 BOM 归并）。
- 同 asset_id 跨镜 kind/target_path 一致；同地不同状态用不同 asset_id；摄影区留空。
- 不臆造，UNSET 登记待补。

## 交稿前自问清单
- [ ] 是否按动作行切镜、duration_tier 选档正确、duration_s 在档内？
- [ ] timeline 是否无缝隙、五元素齐、弹性拍有标注？
- [ ] 空间锚四子字段齐、cast_positions 覆盖全部角色？
- [ ] needs 是否精简、scene 条带 grid_id/cell、外观没写进镜头卡？

## 交到哪
`05-shots/<SHOT>.json`（design）→ 转 [6] 摄影回填 → 过 G04，通过后进 [7]。
