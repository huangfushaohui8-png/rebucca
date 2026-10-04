# 东方宇阳 Rebucca 引入审计 — 任务

版本：1.0.0｜日期：2026-10-04｜状态：执行中

依次核验来源、审计、部署设计和远程交付。任务完成指本期材料完成；漏洞整改、真实摄像头、模型效果及生产上线尚不在执行状态。

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "kind": "task",
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.adoption",
  "doc_version": "1.0.0",
  "spec_revision": 1,
  "spec_doc_version": "1.0.0",
  "spec_sha256": "e0762315f4b9d722a56dc310ba7b66bc2e014550532c44e926f900754792d53e",
  "tasks": [
    {
      "id": "T-001",
      "title": "版本、许可与用户 fork 核验",
      "requirements": [
        "R-001"
      ],
      "depends_on": [],
      "owner": "百望侠",
      "deliverable": "上游来源记录与用户 fork",
      "done_when": [
        "远程仓库存在，版本和文件来源可追溯"
      ],
      "status": "done",
      "evidence": [
        "https://github.com/huangfushaohui8-png/rebucca",
        "上游 SHA 8440b5545fc4f02bad105cbcc1ed09f24a0a2dfd"
      ]
    },
    {
      "id": "T-002",
      "title": "扫描、手工审阅与隔离验证",
      "requirements": [
        "R-002",
        "R-003"
      ],
      "depends_on": [
        "T-001"
      ],
      "owner": "百望侠",
      "deliverable": "docs/security-audit.md 与 docs/security/evidence/",
      "done_when": [
        "工具原始结果、去重统计、主要风险数据流和未覆盖范围均有证据"
      ],
      "status": "done",
      "evidence": [
        "docs/security-audit.md",
        "docs/security/evidence/verification.json",
        "docs/security/evidence/isolated-findings.json"
      ]
    },
    {
      "id": "T-003",
      "title": "部署路径、整改优先级与准入验收",
      "requirements": [
        "R-004"
      ],
      "depends_on": [
        "T-002"
      ],
      "owner": "百望侠",
      "deliverable": "docs/deployment-plan.md",
      "done_when": [
        "端口、容量、隔离、启动兼容性、持久化和回退均写清；区分已验证和建议"
      ],
      "status": "done",
      "evidence": [
        "docs/deployment-plan.md",
        "docs/security/evidence/verification.json"
      ]
    },
    {
      "id": "T-004",
      "title": "GitHub 文档保存与交付核验",
      "requirements": [
        "R-004"
      ],
      "depends_on": [
        "T-003"
      ],
      "owner": "百望侠",
      "deliverable": "文档提交及 PR，远程内容校验记录",
      "done_when": [
        "新增文件远程摘要与本地一致；原产品源码仍匹配被审计上游"
      ],
      "status": "running",
      "evidence": []
    }
  ]
}
```
<!-- /engineering-meta -->
