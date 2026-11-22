# Agent Kernel 项目总览

更新日期：2026-11-15。本文介绍当前工作树，不代表某个已发布 tag 的全部能力，也不构成部署、付费调用或发布授权。

提交范围：介绍与状态同步提交 `17af7db` 未包含付费 Docker 配置、`docker-paid-*` 命令及 `response_sha256` 响应保护。后续单独提交这些实现及其回归测试，必须检查该实现提交自己的 CI，不能沿用文档提交的通过结论；详见[提交边界](local-paid-experience.md#documentation-only-commit-boundary)和[实现跟进](local-paid-experience.md#separate-implementation-follow-up)。历史本地体验不是新克隆后的自动执行指令。

## 定位与目标用户

Agent Kernel 是一个可自托管、可审计、可恢复的 AI Agent 执行平台。它把模型、知识库、工具、权限、人工审批和后台执行组织成可管理的任务系统，而不是只提供一个聊天界面。

目标用户是构建内部 AI 助手的工程团队、需要可控工具执行的应用开发者，以及希望系统学习 Agent 工程的维护者。当前试点聚焦“部署与运维助手”：根据已审查的运维资料回答问题并引用来源，经批准后查询指定 GitHub CI 历史运行。

生产级是工程目标，需要按部署和场景验收，不能从版本号、模块数量或测试通过自动推导。当前更准确的定位是：**具备较完整工程基础、已验证部分真实链路的受控试点平台**。

## 解决的问题与非目标

| 问题 | 提供的机制 | 不能据此承诺 |
| --- | --- | --- |
| 模型不知道团队内部知识 | 文档处理、向量检索、知识库工具和引用 | 回答永远正确或每条引用都支持结论 |
| 模型调用外部系统可能越权 | 参数校验、服务端权限、工具策略和人工审批 | 模型提示词本身构成安全边界 |
| 任务耗时、进程中断、重复领取 | 后台 Worker、持久化状态、租约、检查点和恢复 | 任意外部副作用全局 exactly-once |
| 结果难解释、难回归 | Run 事件、工具记录、Trace、用量和行为 eval | 所有实际故障已被观测或覆盖 |
| 多人使用时范围混淆 | 身份、角色、Workspace 和对象范围检查 | 已完成公网多租户 SaaS 运营验收 |

当前不以模型训练、通用无代码搭建器、任意 shell/浏览器自动化、不可信插件沙箱或多地域托管平台为目标。先验证现有单 Agent 场景，不因参考工程有某个功能就扩大范围。

## 如何使用

主要入口是 Web Workbench、API 和 CLI。Workbench 是任务工作台，不是仅有聊天记录的聊天产品：创建 Agent，上传知识库，解析、分块和索引，提交 Run，查看执行事件与引用，处理审批，再显式续跑。

默认 `make docker-up` 使用 Mock 模型和 Mailpit。真实模型使用需要单独授权的付费配置；Embedding 索引和检索也可能收费。当前维护者体验的匿名 localhost 配置与开启鉴权的试点配置不是同一验收范围。

## 技术选型与取舍

| 层次 | 当前实现 | 选择逻辑和边界 |
| --- | --- | --- |
| 后端 | Python 3.12、FastAPI、Pydantic、Typer | 统一 Agent、数据处理、API 和 CLI；不代表 Node.js 无法实现 |
| 工程工具 | uv、Ruff、严格 mypy、pytest | 锁定依赖，提前发现类型和行为问题；测试仍依赖合理断言 |
| Web | TypeScript、React、Next.js、Playwright | 类型化交互和同源 API 代理；不是直接访问数据库 |
| 持久化 | PostgreSQL、SQLAlchemy、Alembic | 唯一受支持数据库；运行库与可丢弃测试库隔离，无 SQLite 回退 |
| 向量检索 | pgvector、Embedding 适配器 | 与业务记录统一管理；模型或维度变化需要重新索引，不会自动转换旧向量 |
| 后台协调 | Redis + PostgreSQL 执行记录 | Redis 提供队列提示与限流，数据库保存权威状态 |
| 文件 | 本地对象存储、S3/MinIO 兼容适配器 | 当前本地使用持久文件卷，不意味着已有运行中的 MinIO 服务 |
| 模型 | OpenAI、DeepSeek、Mock/Replay 适配 | 隔离服务商差异；当前真实体验使用 DeepSeek 和阿里云 Embedding |
| 运维 | Docker Compose、GitHub Actions、OpenTelemetry 与观测后端 | 单机部署与回归验证；不是现成的高可用集群 |

Python 承担运行时，TypeScript 承担产品交互。保持这一分工，避免迁移语言打断验收。替换模型、存储或工具适配器仍需满足契约与回归测试，不是修改一个名称就能保证兼容。

## 工程架构

采用 **Monorepo + 模块化单体 + 独立 Worker + 可替换适配器**。单仓库不等于单进程，也没有为了模块化而拆出大量微服务。

```text
Web Workbench / CLI
        |
        v
FastAPI 控制面：身份、Workspace、Agent、Run、知识库、审批
        |
        +--> PostgreSQL / pgvector：记录、状态、检查点、向量
        +--> Redis：排队提示、限流
        +--> Object Store：原始文档、解析产物
        |
        v
Worker --> Runtime --> Provider / Tools / Policy / Memory / RAG
                         |
                         v
                   事件、用量、日志、Trace、评测证据
```

这是主要排队执行路径。当前审批续跑仍存在 API 请求内执行路径，不能把所有恢复都描述为异步 Worker durable resume。核心模型不依赖 FastAPI、数据库实现或服务商 SDK，应用层组合运行时和适配器。

| 目录 | 职责 |
| --- | --- |
| `apps/api`、`apps/worker`、`apps/cli`、`apps/web` | HTTP、后台执行、命令行、工作台入口 |
| `packages/kernel-core`、`kernel-identity` | 核心模型、身份与权限领域 |
| `packages/kernel-runtime`、`kernel-providers` | 执行状态与预算、路由、模型请求 |
| `packages/kernel-tools`、`kernel-policy` | 工具协议、参数与执行策略 |
| `packages/kernel-memory`、`kernel-rag` | 记忆上下文、资料处理、检索与引用 |
| `packages/kernel-storage` | 持久化及对象/向量存储实现 |
| `packages/kernel-evals`、`kernel-observability` | 行为评估、报告、遥测 |
| `tests`、`evals`、`deploy`、`docs` | 回归测试、数据集、部署配置、设计与验收记录 |

## 能力与证据矩阵

“已实现”指存在代码路径；“已验证”必须注明测试或实际执行范围；“待完成”指尚缺证据、决定或实现。三者不是可以互相替代的完成标签。下表是能力说明，不是第二份试点进度表。

| 能力 | 已实现 | 已验证的范围 | 待完成或明确边界 |
| --- | --- | --- | --- |
| 运行时 | Run 状态机、原生工具调用、有界多轮、取消、错误与用量记录 | 离线状态/执行回归；一次真实模型-工具-模型 RAG | 完整真实题集；非无限自主执行 |
| 模型路由 | Provider 接口、模型路由、重试与 fallback | Mock/Replay 和适配器测试；DeepSeek 实际生成 | 不是所有服务商都已实测，失败模型切换不保证语义等价 |
| 工具协议 | 注册表、结构化参数、OpenAPI、MCP、风险元数据 | 协议及权限回归、离线请求计数 | 非任意代码沙箱；当前 GitHub 最终回答尚未成功 |
| 人工审批 | 审批与工具记录持久化、批准/拒绝、显式 Resume、契约检查 | 离线批准/拒绝回归；真实暂停、批准、续跑后响应拦截 | 真实 GitHub 成功续答；失败响应私密证据修复尚未实施 |
| 服务端控制面 | 身份/API Key、RBAC、Workspace、对象范围校验 | 鉴权 API/CLI 和完整 Web 首用的有界离线 CI | 公网多租户运营、企业 SSO、数据库级硬隔离不能据此宣称完成 |
| 后台执行 | 队列、租约、心跳、所有权、检查点、退避、卡住任务恢复 | PV2 + PV4 本地候选启停/备份/升级/负载演练已收口 | 外部副作用不保证 exactly-once；S3 需另训 |
| 记忆 | 持久化、范围限制、有限检索、不可信上下文与容量限制 | CF1 disposition 2026-11-22；PV3 R4 含注入/越权拒答门 | 高级语义召回、自动总结与生命周期增强 |
| RAG | 上传、解析、分块、真实 Embedding、pgvector、引用、`kb_search` | 实际 DashScope v3/1024 索引/检索、DeepSeek 引用回答 | 30 题整体质量；混合检索/RRF/重排为条件性后续项 |
| Prompt | PromptRegistry、试点提示词冻结版本与哈希 | 离线请求捕获和冻结材料检查 | CF3：生效版本贯穿 Run、检查点和 eval 的绑定 |
| Workflow / 多 Agent | 单 Agent 执行状态机与工具交互流程 | 当前单 Agent 路径 | CF7：持久化多 Agent DAG 和有范围约束的 handoff；不是已交付的通用图引擎 |
| 可观测 | 指标、日志、Trace、关联信息、本地告警邮件 | O1-O5 中的本地端到端与对应 CI 证据 | 真实外部邮箱送达、高可用运维；费用估算不是账单 |
| 评估 | 单元/集成/Web 测试、持久化 eval、检索/工具/时间线评估、离线 harness | 确定性回归；PV3 R4 冻结 30×2 实模质量门已收口 | PV5 独立用户结果；不能用测试数量代替效果 |

## 安全、观测与部署边界

安全依靠服务端权限、对象范围、工具参数与策略、网络目标约束、审批和检查点校验共同实施。文档、记忆和工具结果都是不可信输入。当前 GitHub 绑定还校验已审查响应的原始字节哈希；变化时阻止外发，不自动更新白名单。

默认本地栈共 13 个服务：API、Worker、Web、PostgreSQL/pgvector、Redis、Prometheus、Blackbox、Grafana、Alloy、Loki、Tempo、Alertmanager、Mailpit。Mailpit 接收成功不是外部邮箱送达。密钥只保存在被 Git 忽略的私密配置中，不能进入源码、聊天或公开日志。

本地 `make docker-up` 为 Docker-only 默认 Mock 入口。测试必须用隔离 PostgreSQL，不能指向当前 Docker 运行库。保留数据卷，不将重建容器等同于删除数据；当前用户资料和凭据不会因本文整理而改变。

## 当前真实体验证据

详细记录见 [本地付费体验](local-paid-experience.md)，不能与离线 CI 或正式试点样本混算。

- RAG Run `6ee6ad17-e47c-4777-b3fe-d4e3deeb9ac0` 成功：两次 DeepSeek 用量记录、一次成功 `kb_search`、文档与分块引用；是一个真实样本，不是 30 题验收。
- GitHub Run `e737c1a6-72fe-485e-9d5a-82888bbaee2a` 经人工批准后续跑，在 `external_response_review_required` 处失败；没有最终回答，也没有把失败响应继续交给模型。
- 后续获准的只读检查取得的响应与旧白名单原文一致。失败那次的响应原文未保留，因此具体差异未知，不能断言是 GitHub 元数据变化，也不能据此放宽校验。
- 费用估算字段为零不等于免费。USD 2 首批、USD 10 总额和 USD 0.25/任务是操作限额，不是服务商保证的硬扣费上限；账单核对仍未完成。
- 这是关闭鉴权的单用户 localhost 体验；鉴权 Web 的离线 CI 是另一条证据，不据此推断真实共享多租户或独立用户试点成功。

本地体验发生时包含未提交的配置和响应校验改动，现按独立实现提交审查。旧 commit 的绿色 CI 不能验证后续实现。本次提交不重跑以上任务，不调用付费模型，不更新 Docker；失败响应的私密证据补齐仍未实施。

## 后续规划与完成口径

[PV1-PV6 试点计划](real-scenario-pilot-plan.md)是唯一试点任务与状态台账；[CF1-CF8 计划](reference-follow-up-plan.md)拥有参考工程补齐项。本文不增加开发天数或新的功能阶段。

1. 先处理当前体验阻塞：待恢复该工作时，最小化补齐失败响应私密证据与回归，再通过实际工具路径诊断。该修复当前暂停，尚未实施；不重跑任务、不自动更换哈希或关闭审批。
2. 保留 PV1 已定稿的技术范围；PV2 bounded 演练门与 CF1 disposition 已于 2026-11-22 收口。一次本地付费体验仍不自动解除 PV5 门槛。
3. PV3 质量门已于 2026-11-22 在 R4（prompt v2、冻结 30×2）收口，见 [pv3-closure](pilots/pv3-closure.md)。
4. PV4 运维门已于 2026-11-22 收口（启停/备份恢复/升级回滚/有界 mock 负载），见 [pv4-closure](pilots/pv4-closure.md)。
5. PV5/PV6 已于 2026-11-22 **暂停待办**（缺独立试用者/日期），恢复清单见 [pv5-pv6-pending](pilots/pv5-pv6-pending.md)。维护者体验不代替独立试用；PV6 不是自动发布。
6. CF3/CF4 的 Prompt 绑定、会话/任务和可恢复流式体验保持 deferred；CF5-CF7 的高级记忆、失败到评测的工作流、多 Agent 只按后续批准范围推进。CF8 的 RRF/混合检索/重排仅在有证据表明检索是瓶颈时再评估。

下一阶段的标准不是功能清单更长，而是在确定场景里证明系统有用、可控、可恢复。维护者学习按 [学习机制](pilot-learning-guide.md)记录设计取舍、故障定位与测试实践，不将项目完成等同于个人已经达到专家水平。

## 文档导航与状态维护

- [架构](architecture.md)、[十视角机制说明](architecture-ten-perspectives.md)、[技术栈](tech-stack.md)、[模块边界](modules.md)：工程结构及其理由。
- [PV2 证据](pilots/pv2-closure.md)、[PV3 收口](pilots/pv3-closure.md)、[PV4 收口](pilots/pv4-closure.md)、[Web 验收](pilots/pv2-web-acceptance.md)、[CF1 风险](reviews/cf1-risk-disposition.md)：对应范围的通过项和未决项。
- [观测验收台账](observability-completion-plan.md)：日志、Trace、告警及外部邮件门槛。
- [本地付费体验](local-paid-experience.md)：实际本地观察；不是新试点计划或重复执行指令。

更新时先修改证据所属台账，再同步 README 和本文摘要。历史阶段记录保留当时事实并标明时间范围；冻结资料、答案和提示词不得为了消除过时措辞而静默改写或重算哈希。

例如，冻结来源 `observability-completion-plan.md` 中早期 PV 阶段摘要不再代表当前试点进展；该文件仍用于其 O1-O5 观测证据，PV 状态以本文链接的试点台账为准。本次不改动这些已冻结来源。
