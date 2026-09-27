# Video backend adapters

`submit_take.py` 在付费提交时加载这里的一个适配器，文件名由 gen.json 的
`model` 推导（小写、去点、空格变 `_`），例如 model `h3` → `h3.py`。视频生成
后端的差异（提交端点、异步轮询、鉴权、结果下载、seed 回传）隔离在适配器内，
submit_take 本身保持模型无关。

## 适配器接口（必须实现）

```python
def submit_and_wait(*, gen, root):
    """Submit one video job and wait for the result.

    gen  : 08-prompts/<SHOT>.gen.json（workflow/mode/duration/ref_* 等全部参数）
    root : 项目根（绝对路径）

    return: {
      "bytes": <mp4 bytes>,          # 成片，由 submit_take 落 09-takes/
      "task_id": <platform task id>, # 写入 provenance
      "seed": <integer>,             # 写入 provenance（平台不回传则给 None）
    }
    """
```

## 约定

- 凭证从环境变量读取，缺凭证明确报错，不静默失败；
- 付费请求只此一处真正发出；submit_take 已在调用前完成 freeze 指纹核对与用户确认；
- 不得在适配器内改 BOM/gen 状态——provenance 由 submit_take 统一回填；
- 端点、workflow id、模型名只能取自 gen/profile，不硬编码；
- 一个模型一个文件；新增模型不改 submit_take.py。
