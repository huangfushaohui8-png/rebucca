# 东方宇阳 Rebucca 引入审计 — 任务

版本：1.1.0｜日期：2026-10-11｜状态：本期引入与审计材料已交付

依次核验来源、审计、部署设计和远程交付。任务完成指本期材料完成；漏洞整改、真实摄像头、模型效果及生产上线尚不在执行状态。

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "kind": "task",
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.adoption",
  "doc_version": "1.1.0",
  "spec_revision": 2,
  "spec_doc_version": "1.1.0",
  "spec_sha256": "b06b744be6aa777429a989abbd128ef9822e26a1fbd403da01ee2cdf4e9f7060",
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
      "status": "done",
      "evidence": [
        "docs/security/evidence/publication.json",
        "https://github.com/huangfushaohui8-png/rebucca/pull/1",
        "远程文件核验提交 3b3caaabeada0e38b9e9837c77f984927880c2b2"
      ]
    },
    {
      "id": "T-005",
      "title": "补齐 F01/F02 模块契约",
      "requirements": [
        "R-005"
      ],
      "depends_on": [
        "T-004"
      ],
      "owner": "百望侠",
      "deliverable": "独立模块三文档、范围版本清单和权限定义",
      "done_when": [
        "对应模块条目满足预设判据并记录实际证据；T-008 只要求 Draft PR，不要求合并或生产上线"
      ],
      "status": "backlog",
      "evidence": []
    },
    {
      "id": "T-006",
      "title": "实现截图/回调及发送兼容",
      "requirements": [
        "R-005"
      ],
      "depends_on": [
        "T-005"
      ],
      "owner": "百望侠",
      "deliverable": "受影响源码与可复现隔离测试入口",
      "done_when": [
        "对应模块条目满足预设判据并记录实际证据；T-008 只要求 Draft PR，不要求合并或生产上线"
      ],
      "status": "backlog",
      "evidence": []
    },
    {
      "id": "T-007",
      "title": "隔离行为验证与证据",
      "requirements": [
        "R-005"
      ],
      "depends_on": [
        "T-006"
      ],
      "owner": "百望侠",
      "deliverable": "测试日志、提交/环境/边界记录",
      "done_when": [
        "对应模块条目满足预设判据并记录实际证据；T-008 只要求 Draft PR，不要求合并或生产上线"
      ],
      "status": "backlog",
      "evidence": []
    },
    {
      "id": "T-008",
      "title": "保存独立 Draft PR 和回退说明",
      "requirements": [
        "R-005"
      ],
      "depends_on": [
        "T-007"
      ],
      "owner": "百望侠",
      "deliverable": "固定提交、PR 及剩余门禁",
      "done_when": [
        "对应模块条目满足预设判据并记录实际证据；T-008 只要求 Draft PR，不要求合并或生产上线"
      ],
      "status": "backlog",
      "evidence": []
    }
  ]
}
```
<!-- /engineering-meta -->
