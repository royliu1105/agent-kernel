# D11: troubleshooting

本地脱敏摘要草案；待人工审核，未授权外发或导入知识库。
仅描述版本化文档约定，不证明当前 Docker 已部署该版本。

## D11-S1: 先分层定位

默认从 make docker-status、make docker-logs SERVICE=api、make docker-logs SERVICE=worker 和 make docker-check 排查。看到容器不代表 API 已监听：检查服务启动、迁移错误、端口冲突以及是否只启动了数据库等依赖。不要默认启动第二套宿主机 API/Worker/Web。

## D11-S2: 检索前置条件

检索只搜索已经索引的 chunks。顺序为上传、ingest、chunk、index、search；检查知识库 ID、chunk 是否完成以及 embedding_count 是否为正。仅有上传文件或成功返回 mock 结果不能证明真实语义质量。

## D11-S3: 证据范围

本材料是通用排查指引，不包含昨日事故根因、实际账单或某次灾备耗时。没有对应运行证据时应承认未知，不能从配置目标或历史测试推断真实生产结果。
