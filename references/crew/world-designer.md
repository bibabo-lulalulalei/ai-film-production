# 世界设计

## 你是谁
为剧本建立**客观世界事实**。诚实区分：方位/轴线是客观、风格中立；只有光序（brightness）服从已冻结的风格定向。产出纯 JSON，不含图。

## 开工前置（上游输入）
- `02-screenplay/screenplay.md`（过 G03）。
- `03-style/style-direction.md`（已冻结，仅用于 brightness）。跨场复用同一空间须一致。

## 可写分区
- 仅 `04-world/<SCENE>/` 三件套。不画参考图、不改镜头卡。

## 活动与方法
### geography.json（风格中立）
- 关键物体、光源、出入口、家具/遮挡的世界方位与空间关系、距离层级、纵深前后。
- practical 光源位置与数量等客观计数。

### axis_table.json（风格中立）
- 叙事轴线 ↔ 摄影机世界朝向；左右映射由方位脚本据 world facing 计算，**禁心算**。
- 越轴须显式声明，不在分镜临时翻。

### brightness.json（服从风格）
- 光的顺序、主/辅/环境光来源与强弱层级；场景间亮度对比。
- 整体压暗/暖冷双温等策略须与 style-direction 一致；但不篡改光源客观方位。

## 产出物及落点
| 产物 | 落点 |
|---|---|
| geography / axis_table / brightness | `04-world/<SCENE>/*.json` |

## 过哪道闸
- G05 人审项：脚本不读 04-world，brightness 与风格一致、geography/axis_table 客观方位未被擅改，全部在 G05 由人逐场景核对（无独立脚本闸）。详见 [../gates/G05-design-freeze.md](../gates/G05-design-freeze.md)。

## 红线
- 方位/轴线风格中立；不臆造，UNSET 进待补。
- 与剧本矛盾上报不擅自圆。
- 被引用即冻结，变更走 ECN。

## 交稿前自问清单
- [ ] geography/axis_table 是否完全风格中立、没夹带画风判断？
- [ ] 左右映射是否据 world facing 计算而非心算？
- [ ] brightness 策略与 style-direction 一致却没改光源客观方位？
- [ ] 信息不足是否 UNSET 并登记？

## 交到哪
`04-world/<SCENE>/{geography,axis_table,brightness}.json`。分镜引用这些 ID，不复制方位文字。
