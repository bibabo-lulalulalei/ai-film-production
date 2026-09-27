根据以下设计要求生成{{layout_phrase}}：场景「{{name}}」（{{asset_id}}·{{grid_id}}）。

【核心场景资产与画风统一控制】（在主体块内彻底描述一次，全部视图逐字一致；每个构件在此命名并锁定外观——这是唯一一处描述它，下方逐视图一律不重述、不重新形容）
- 场景身份：{{identity_line}}
- 视觉风格：{{visual_style}}
- 空间平面：{{floor_plan}}
- 纵深层：
{{depth_block}}
- 遮挡关系：{{occlusion_block}}
- 色彩与光影：
{{lighting_block}}
- 色彩锚（唯一色板；光源色单列）：
{{color_anchors}}
- 建筑构件与材质（逐一命名锁定）：
{{materials}}
- 固定陈设（逐一命名锁定）：
{{furnishings_block}}
- 空气与地形：{{environment_block}}

【画面构图与分区排版】
{{layout_instruction}}
{{continuity_line}}

【逐视图内容】（铁律：同一空间，每格**只写本格差异**——机位/角度＋该格独有的前景或须见的已命名构件；共享构件只引用其名、不重述外观；不得借写差异之名重新形容主体）
{{view_blocks}}

【画面卫生】
- 画面干净利落、专业规范；无人物（空场，人物在镜头阶段以定妆 sheet 加入）；无文字、无水印、无 LOGO、无品牌标识。
- 全局负向（画风规格＋本卡负向，统一排除）：
{{global_negative}}
- 风格禁词（出现即废）：{{forbidden}}

<!-- === 分隔线：以下为占位取值表，渲染时不进成品 ===
{{name}}               <- identity.name
{{asset_id}}           <- asset_id
{{grid_id}}            <- grids[].grid_id
{{layout_phrase}}      <- layout: single→一张完整单图；2x2→一组2×2四宫格；3x3→一组3×3九宫格
{{identity_line}}      <- identity: interior_exterior/time_of_day/season/weather
{{visual_style}}       <- style-spec.json 槽位按场景拼装（脚本提取，不在此硬编码）
{{floor_plan}}         <- layout.floor_plan
{{depth_block}}        <- layout.depth_layers[] layer+contents
{{occlusion_block}}    <- layout.occlusion
{{lighting_block}}     <- lighting: practical_sources/ambient/key_to_fill_ratio/overall_exposure
{{color_anchors}}      <- palette[] name+hex ＋ practical_sources[] type+color_hex（标光源色）
{{materials}}          <- architecture[] element/material/color_hex/size_note/condition/opening_view
{{furnishings_block}} <- furnishings[] prop_id+position（无则写「无」）
{{environment_block}}  <- air / terrain_vegetation
{{layout_instruction}} <- single: 单图无分隔线；2x2/3x3: Four-grid split screen layout
                          受控拼版句（等大/分隔线/无重叠偏移/全一致）
{{continuity_line}}    <- 非首张 grid: 垫上一张 target_path；首张为空
{{view_blocks}}        <- cells[] 编号逐行，仅差异: 格位中文名＋机位/角度＋独有物/须见构件（不重述共享外观、不写 serves_shots）
{{global_negative}}    <- style-spec negative/medium.not/line.forbidden ＋卡 negative（去重）
{{negative}}           <- 已并入 {{global_negative}}（acceptance.negative 统一在全局负向）
{{forbidden}}          <- style-checks.json forbidden_terms
====================================================== -->
