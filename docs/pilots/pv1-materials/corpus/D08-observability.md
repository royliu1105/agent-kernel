# D08: observability

本地脱敏摘要草案；待人工审核，未授权外发或导入知识库。
仅描述版本化文档约定，不证明当前 Docker 已部署该版本。

## D08-S1: 关联与采集

使用持久化 Run trace ID 关联执行操作，真实模型、工具及重试尝试应有对应 span。审批续跑可能在同一 trace 下产生另一个 root operation，不等于跨进程重启一直存活的单个 span。API 与 Worker 指标独立，需分别抓取，不能只抓 API 就声称覆盖 Worker。

## D08-S2: 日志安全

结构化日志只保留审核过的标识符和计数等字段；输入、消息、参数、结果、文档及异常文本不应直接输出。Trace exporter 使用脱敏包装，不能另加 raw exporter 绕过它。该边界不是通用自然语言隐私识别器，不应启用 SDK wire/debug 或 SQLAlchemy echo。

## D08-S3: 费用与送达证据

指标是进程级估算，重启可能重置，不是账单。持久化 usage 也不等于供应商发票；adapter 未提供定价而显示 estimated cost 为零，不证明免费。需要独立账单核对。日志、Trace 或报警触发本身均不能单独证明外部邮件收件成功。
