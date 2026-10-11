# 东方宇阳 Rebucca 引入记录

2026-10-04 从 `yuturuishi/rebucca` 导入版本 1.005，完整上游提交为 `8440b5545fc4f02bad105cbcc1ed09f24a0a2dfd`。用户副本保留上游历史与原始代码。

**生产安全准入仍 FAIL，未部署产品。** 2026-10-04 的引入与审计已在 PR #1 合并；2026-10-11 本轮 F01/F02 候选修复保存到独立 [Draft PR #2](https://github.com/huangfushaohui8-png/rebucca/pull/2)，尚未合并到 main。截图增加当前用户及对象权限、私有缓存和无 Shell 执行；四个内部回调增加独立服务身份及回环/对象边界。固定代码 `21ded3072827a77703824ca2692d00e453e3c4b6` 的隔离容器 51 项测试全部通过，含真实 FFmpeg 合成 RTSP 取帧。角色越权、SQL、路径、依赖及外联等其余发现仍保留整改门禁，附带二进制/模型、真实 ZLM/SIP 及完整产品服务未验收。

- [安全审计与后门检查边界](docs/security-audit.md)
- [部署、整改顺序与验收方案](docs/deployment-plan.md)
- [F01/F02 修复、隔离实测、固定提交与回退](docs/security/f01-f02-remediation.md)
- [扫描、版本和隔离验证证据](docs/security/evidence/verification.json)
- 工程入口：[AGENTS.md](AGENTS.md)、[spec.md](spec.md)、[task.md](task.md)、[test-spec.md](test-spec.md)，登记历史引入审计及本轮两个整改模块；未将全产品宣称为已完成工程化。

公开 fork 只保存公开源码、审计与合成验证，生产口令、数据库、客户视频和运行配置禁止提交。平台 MIT 许可与模型、播放器等第三方许可分别核验。
