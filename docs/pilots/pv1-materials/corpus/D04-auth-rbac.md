# D04: auth-rbac

本地脱敏摘要草案；待人工审核，未授权外发或导入知识库。
仅描述版本化文档约定，不证明当前 Docker 已部署该版本。

## D04-S1: 权限与工作区

共享或部署环境必须启用 API key 鉴权。viewer 是只读角色，不能审批或续跑；权限不足返回 403。Run、知识库、记忆和派生对象按认证工作区隔离；记忆的业务 scope 字符串不授予访问权限。

## D04-S2: 审批与身份

审批范围通过 approval -> run -> workspace 推导。跨工作区审批详情或决策返回 404；续跑先拒绝其他工作区的审批 ID。审核人来自认证 principal，不由模型或请求中的身份描述决定。

## D04-S3: 凭据传递

CLI 从 AGENT_KERNEL_API_KEY 读取凭据并使用 Authorization: Bearer 请求头。凭据应通过秘密管理或不跟踪的私密环境加载，不放入 NEXT_PUBLIC_*。localhost 之外使用 HTTPS 并确认受信任 API 地址。Web 代理鉴权是独立事项，不能把未鉴权的本地页面视为已完成鉴权的试点入口。
