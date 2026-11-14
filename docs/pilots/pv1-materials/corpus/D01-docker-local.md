# D01: docker-local

本地脱敏摘要草案；待人工审核，未授权外发或导入知识库。
仅描述版本化文档约定，不证明当前 Docker 已部署该版本。

## D01-S1: 启动与停止

本地默认通过 make docker-up 或 sh scripts/local-stack.sh up 启动。该命令会按需构建镜像、执行迁移并启动 Compose 服务，不是只启动数据库。make docker-stop 停止服务；make docker-down 移除容器和网络但保留数据卷。不得为了重启删除数据卷或私密配置。命令仅供说明，不构成本次执行授权。

## D01-S2: 服务与入口

默认项目包含 API、Worker、Web、PostgreSQL/pgvector、Redis、Prometheus、Blackbox、Grafana、Alloy、Loki、Tempo、Alertmanager、Mailpit 共 13 个服务。默认本机入口：Web 3000，API 文档 8000/docs，就绪检查 8000/readyz，Grafana 3090，Prometheus 9090，Alertmanager 9093，Mailpit 8025。地址均为 127.0.0.1；PostgreSQL、Redis 和 Worker 指标仅在内部网络提供。

## D01-S3: 凭据与边界

私密配置存放在被 Git 忽略且权限受限的运行目录，凭据不得写入源码、聊天、日志或浏览器公开变量。默认本地配置关闭 API 鉴权，只适用于可信单用户本机，不能暴露到局域网或公网。默认模型和 Embedding 使用 mock，邮件送到本地 Mailpit；这不证明外部邮箱送达，也不授权真实模型调用。
