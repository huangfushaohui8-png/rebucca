# 东方宇阳 Rebucca — 验证规格

版本：1.1.1｜日期：2026-10-11｜状态：历史审计材料及本轮局部隔离测试通过；产品准入仍 FAIL

TS-001～TS-004 保留历史审计材料验收；TS-005 仅表示本轮局部权限与执行边界的隔离验证通过。真实媒体组件、完整服务、独立复核和生产门禁另列 NOT_RUN/FAIL，不能用结构检查或局部 PASS 替代上线准入。

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "kind": "test-spec",
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.adoption",
  "doc_version": "1.1.1",
  "spec_revision": 2,
  "spec_doc_version": "1.1.0",
  "spec_sha256": "b06b744be6aa777429a989abbd128ef9822e26a1fbd403da01ee2cdf4e9f7060",
  "tests": [
    {
      "id": "TS-001",
      "title": "上游与 fork 身份核验",
      "requirements": [
        "R-001"
      ],
      "preconditions": "固定上游 SHA；公开源码与授权 GitHub/本地隔离环境可访问",
      "steps": [
        "比对完整 SHA、LICENSE 和默认分支",
        "确认原始文件继承关系"
      ],
      "expected": [
        "上游固定版本和用户副本可追溯"
      ],
      "status": "PASS",
      "evidence": [
        "docs/security/evidence/source.json",
        "用户 fork main 经 GitHub API 核验与上游 SHA 一致"
      ]
    },
    {
      "id": "TS-002",
      "title": "扫描与主要风险证据完整",
      "requirements": [
        "R-002"
      ],
      "preconditions": "固定上游 SHA；公开源码与授权 GitHub/本地隔离环境可访问",
      "steps": [
        "读取语法、Bandit、依赖检索结果",
        "独立预设风险判据后进行隔离数据流验证"
      ],
      "expected": [
        "无静默跳过扫描；发现/误报/未运行项分类清楚",
        "检测风险的试验成功不等于应用安全检查通过"
      ],
      "status": "PASS",
      "evidence": [
        "docs/security/evidence/verification.json",
        "docs/security/evidence/bandit.json",
        "docs/security/evidence/isolated-findings.json"
      ]
    },
    {
      "id": "TS-003",
      "title": "后门与外联结论边界",
      "requirements": [
        "R-003"
      ],
      "preconditions": "固定上游 SHA；公开源码与授权 GitHub/本地隔离环境可访问",
      "steps": [
        "比对实际外联路径、传输内容、触发条件",
        "核查二进制和模型摘要、未执行范围"
      ],
      "expected": [
        "没有过度承诺无后门；遥测与恶意意图不混同"
      ],
      "status": "PASS",
      "evidence": [
        "docs/security-audit.md 外联与后门判断",
        "docs/security/evidence/inventory.json"
      ]
    },
    {
      "id": "TS-004",
      "title": "部署方案可审阅与 GitHub 可恢复",
      "requirements": [
        "R-004"
      ],
      "preconditions": "固定上游 SHA；公开源码与授权 GitHub/本地隔离环境可访问",
      "steps": [
        "核对 Mac/Docker 事实和硬件建议假设",
        "核对端口隔离、版本锁、准入门槛及回退",
        "比对远程提交文件摘要"
      ],
      "expected": [
        "本期不伪称部署成功",
        "报告与工程材料保存，源码基准可重建"
      ],
      "status": "PASS",
      "evidence": [
        "docs/deployment-plan.md",
        "docs/security/evidence/verification.json 设备能力与未运行项",
        "docs/security/evidence/publication.json 166 原文件及 18 新文件比对通过"
      ]
    },
    {
      "id": "TS-005",
      "title": "本轮模块边界、固定版本与回退证据",
      "requirements": [
        "R-005"
      ],
      "preconditions": "模块 ready；新建合成库，禁用 GlobalUtils/后台线程导入副作用",
      "steps": [
        "运行截图及回调隔离套件",
        "核对提交、容器隔离、PR、真实服务未运行项和回退",
        "确认原风险门禁未被放宽"
      ],
      "expected": [
        "两模块局部行为通过；附固定版本",
        "整体生产准入仍 FAIL，真实依赖与独立复核未验收有记录"
      ],
      "status": "PASS",
      "evidence": [
        "docs/security/evidence/f01-f02/docker-results.json",
        "docs/security/evidence/f01-f02/source-manifest.json",
        "docs/security/evidence/f01-f02/review-summary.json",
        "https://github.com/huangfushaohui8-png/rebucca/pull/2"
      ]
    }
  ]
}
```
<!-- /engineering-meta -->
