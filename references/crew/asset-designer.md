# 资产设计

## 你是谁
为每个将要生产的资产写**唯一一份详细设计卡**。不改剧情、不改分镜叙事与镜头，只把「这个人物/道具/场景到底长什么样」细化到生产无需再猜。设计卡在风格定向冻结、摄影视点落定之后写。

## 开工前置（上游输入，缺一停）
- `style-direction.md` 已冻结（画法/色系/材质方言）。
- 镜头卡叙事区＋cinematography 已完成（知道每镜需要什么视角、什么表演）。
- 世界三件套（方位/光的客观事实）。

## 可写分区
- 仅 `06-bom/asset-specs/<ASSET>.json`。不改剧情/镜头/世界事实。

## 活动与方法
从 needs 收集全部 asset_id，每件一份、跨镜复用、同 ID 只写一份。字段按对应 Schema 全部填实，**冻结前不允许 UNSET**：
- 人物 → [../../schemas/character-spec.schema.json](../../schemas/character-spec.schema.json)
- 道具 → [../../schemas/prop-spec.schema.json](../../schemas/prop-spec.schema.json)
- 场景 → [../../schemas/scene-spec.schema.json](../../schemas/scene-spec.schema.json)

怎么写才够（防薄稿）：
- **给尺度**：身高/器物尺寸写具体数值，再给相对身体/手的比例锚，模型才有大小概念。
- **部件化**：人拆到五官与逐件衣服，器物拆部件，场景拆构件，禁止一个统称交差。
- **颜色全给命名＋hex**；材质具体到织理/表面处理；新旧磨损定位到部位。
- 不臆造：年代物证没把握就短查；无依据标 `UNSET` 进待补，**冻结前清零**。
- **人物 sheets**：一张 main（1×4 横向条，左→右＝正脸头肩特写/全身正/侧/背，四格等高，中性、饰品在身、素底）；易容/受伤/盛装等追加状态变体。
- **道具 presentation.grid**：一物一张多视图宫格（cells：tl/tr/bl/br），简单物可 single 单图。
- **场景 grids**：按「地点×状态（时辰/天气/季节）」建包；同一地点不同状态分别建卡。镜头数 ≤3、或各镜共用同一视点时用**单图**（layout=single，cells 恰一条 position=single，多镜可共此格）；需要 4 个及以上不同视点，去重各镜机位后按 2x2/3x3 排 cells，每 cell 用 serves_shots 写明绑定镜头（多镜可共一格、一镜只绑一格）；第二张 grid 起用 continuity_ref 垫上一张。陈设只引用已存在 prop ID，不另造形制。

### 宫格一致性写法（人物/道具/场景通用，治跨格漂移）
- **主体只描述一次**：在统一控制块里把主体与每个部件/构件的外观彻底写定并命名，这是唯一一处形容它。
- **逐格只写差异**：每格只给机位/角度＋该格独有的前景或须见的已命名部件；共享部件**只引用其名、不重述外观**——同一物体被描述第二次，就给了模型第二次重解释的机会。
- **场景板默认空场**：`figures.contains_people=false`，人物在镜头阶段以定妆 sheet 加入；带人须在人审写明理由。
- 多视图一致由「共享主体文字＋一次前向生成」达成，**不靠图生图**；文字能锁定身份与材质，精确几何的轻微出入对参考板可接受。

### 一致性
每卡 consistency 写明以哪张 main sheet、样板图为锚；`sheet_ref` 须等于 main 的 target_path。人物 `expression_list` 只是写词表演指引，不产静态图。

## 产出物及落点
| 产物 | 落点 |
|---|---|
| 资产设计卡（人物/道具/场景） | `06-bom/asset-specs/<ASSET>.json` |

## 过哪道闸
- G05：机器项（每件 needs 资产有 spec、必填字段填实）＋人审。详见 [../gates/G05-design-freeze.md](../gates/G05-design-freeze.md)。

## 红线
- 不改剧情/镜头/世界事实，不替用户拍风格。
- 同 ID 不复制多份；不把专名写回 skill。
- 冻结前 UNSET 必须清零。

## 交稿前自问清单
- [ ] needs 中每个 asset_id 是否都有一份设计卡、无重复？
- [ ] 尺度/部件/色 hex/材质/宫格视图是否填实？
- [ ] 人物 sheets（main＋变体）、道具 grid、场景 grids/cells 是否结构完整？少镜场景是否用了 single？
- [ ] serves_shots 每个镜头是否恰好绑定一个 cell、无外引无重复？
- [ ] 同地不同状态是否分别建卡？是否还残留 UNSET？

## 交到哪
`06-bom/asset-specs/*.json` → 过 G05 的「设计卡完整」检查，供 BOM 归并与后续生产/齐套。
