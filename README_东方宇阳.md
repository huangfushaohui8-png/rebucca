# 东方宇阳 Rebucca 引入记录

2026-10-04 从 `yuturuishi/rebucca` 导入版本 1.005，完整上游提交为 `8440b5545fc4f02bad105cbcc1ed09f24a0a2dfd`。用户副本保留上游历史与原始代码。

**当前仅完成引入与审计，未通过生产安全准入。** 已确认匿名命令拼接、内部回调无鉴权、角色越权、SQL 注入和下载路径越界等问题；尚未证明附带二进制和模型无后门。本次不把原版启动到用户机器。

- [安全审计与后门检查边界](docs/security-audit.md)
- [部署、整改顺序与验收方案](docs/deployment-plan.md)
- [扫描、版本和隔离验证证据](docs/security/evidence/verification.json)
- 工程入口：[AGENTS.md](AGENTS.md)、[spec.md](spec.md)、[task.md](task.md)、[test-spec.md](test-spec.md)，仅登记本期引入审计范围；未将全产品宣称为已完成工程化。

公开 fork 只保存公开源码、审计与合成验证，生产口令、数据库、客户视频和运行配置禁止提交。平台 MIT 许可与模型、播放器等第三方许可分别核验。
