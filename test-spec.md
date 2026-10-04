# 东方宇阳 Rebucca 引入审计 — 验证规格

版本：1.0.0｜日期：2026-10-04｜状态：判据已定版

这里的 PASS 只表示审计材料满足独立判据。应用的安全边界、真实视频功能、完整部署检查在报告中单列 FAIL/NOT_RUN，不能用文档检查的 PASS 替代上线准入。

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "kind": "test-spec",
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.adoption",
  "doc_version": "1.0.0",
  "spec_revision": 1,
  "spec_doc_version": "1.0.0",
  "spec_sha256": "e0762315f4b9d722a56dc310ba7b66bc2e014550532c44e926f900754792d53e",
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
      "status": "NOT_RUN",
      "evidence": []
    }
  ]
}
```
<!-- /engineering-meta -->
