# D02: postgresql-only

本地脱敏摘要草案；待人工审核，未授权外发或导入知识库。
仅描述版本化文档约定，不证明当前 Docker 已部署该版本。

## D02-S1: 唯一数据库

开发、测试和部署统一使用 PostgreSQL，默认 Docker 包含 pgvector。Docker 配置之外必须提供有效 DATABASE_URL；缺失或不支持的 URL 不会回退到 SQLite。

## D02-S2: 测试隔离

测试使用独立 agent-kernel-test 项目、回环端口 55432 和 tmpfs，不使用 agent-kernel-local 的数据卷。测试连接由 AGENT_KERNEL_TEST_POSTGRES_URL 明确指定，而不是从运行环境 DATABASE_URL 取值。每个测试场景创建并清理独立随机 schema。

## D02-S3: 保护条件

测试 URL 只能指向显式回环地址，数据库名必须满足测试命名规则，禁止通过 URL 参数覆盖连接目的地或 search path。命名检查不是访问控制，仍必须使用独立测试凭据。不能把测试或恢复演练指向当前业务库。
