# 工具目录（Optional Tools）

脱离外部框架封装、可独立运行的命令行工具，供流水线各环节调用。
与 `scripts/`（机械派生）和 `validation/`（闸机校验）不同：这些是**按需使用的
实用工具**，不跑也不影响流水线正确性，但在需要托管文件、抽帧、调研时
直接可用，不必临时找办法。

## 工具清单

| 工具 | 用途 | 流水线环节 |
|---|---|---|
| [`s3/upload.py`](s3/upload.py) | 本地文件或远程 URL 上传 S3，返回 CDN 链接 | [13][14]：H3 的参考图/音需 URL，data URI 不稳时用它托管 |
| [`video/ffmpeg_tool.py`](video/ffmpeg_tool.py) | 抽首帧/尾帧/指定帧 | [14]：出片后抽尾帧作下一镜首帧锚（尾帧链） |
| [`search/web_search.py`](search/web_search.py) | Smart Search 联网**文本**搜索，需凭证 | [2]：同类作品/模型文本调研 |

> 流水线**不收集参考图片**：风格候选以文字视觉规格承载，故无图片搜索/下载工具。

## 用法示例

```bash
# 上传参考图拿到可提交的 URL（可一次多个）
python tools/s3/upload.py 07-assets/characters/LIN/LIN_sheet.png --prefix ref/

# 出片后抽尾帧（路径写该镜 tail.target_path）
python tools/video/ffmpeg_tool.py frame 09-takes/S001/S001.mp4 09-takes/S001/S001_tail.png --tail

# 同类作品文本调研（Smart Search，需凭证）
python tools/search/web_search.py "古典志怪 单元剧 夜景 动画" -n 8
```

> **调研路径备注**：
> - ⚠ **2026-09-24**：Claude 内置 WebSearch 当前 403（Volcano Ark 未开通联网
>   搜索权限），开通后可作为另一条文本调研路径。
> - web_search.py 无凭证时会明确报错并提示如何配置（不静默失败）。

## 配置（凭证不进 skill）

每个工具从**环境变量**读配置，也支持 `--config <KEY=VALUE 文件>`；S3 还会自动
读 `tools/s3/s3.env`：

| 工具 | 变量 |
|---|---|
| s3 | `OSS_ENDPOINT_URL` `OSS_BUCKET_NAME` `OSS_ACCESS_KEY_ID` `OSS_SECRET_KEY_SECRET` `OSS_ANTI_THEFT_CHAIN`（模板：[s3/s3.env.example](s3/s3.env.example)） |
| web_search | `SEARCH_ENGINE_HOST` `SEARCH_ENGINE_SUBSCRIPTION_KEY` |
| video | 无，仅需系统 PATH 有 ffmpeg |

## 依赖

- 全部工具：Python 3 + `httpx`（pip install httpx）
- s3 另需 `boto3`；video 需 [ffmpeg](https://www.gyan.dev/ffmpeg/builds/)
- 缺少依赖时工具会打印明确的安装提示，不会静默失败。
