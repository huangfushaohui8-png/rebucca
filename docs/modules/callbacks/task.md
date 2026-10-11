# Rebucca 内部回调模块

版本：1.0.1｜日期：2026-10-11｜状态：本轮局部实现及隔离测试通过；真实服务未验收｜责任：百望侠（自检，独立复核待进行）

继承根规格 rebucca.adoption 1.1.0 的业务价值和安全边界，只覆盖 F01/F02 受影响流程；不将整个产品工程化。

先更新契约，再实现安全边界，最后隔离验证并进入唯一 Draft PR。真实媒体/生产验收另行，当前交付不需要合并。

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.callbacks",
  "doc_version": "1.0.1",
  "spec_revision": 1,
  "spec_doc_version": "1.0.0",
  "spec_sha256": "2b5ecb7900747e78639b278978c71e81cdd132a26b23c7778dced7d44301cfb2",
  "kind": "task",
  "tasks": [
    {
      "id": "T-001",
      "title": "实现本模块安全边界及正常请求兼容",
      "requirements": [
        "R-001",
        "R-002",
        "R-003"
      ],
      "depends_on": [],
      "owner": "百望侠",
      "deliverable": "安全源码、调用方及隔离套件",
      "done_when": [
        "行为满足全部预设要求；没有引入匿名/跨服务放行"
      ],
      "status": "done",
      "evidence": [
        "app/security.py",
        "app/views/InnerlView.py",
        "app/utils/GB28181SipServer.py",
        "app/utils/MediaServerManager.py",
        "固定代码 21ded3072827a77703824ca2692d00e453e3c4b6"
      ]
    },
    {
      "id": "T-002",
      "title": "运行隔离测试并记录回退与剩余门禁",
      "requirements": [
        "R-001",
        "R-002",
        "R-003"
      ],
      "depends_on": [
        "T-001"
      ],
      "owner": "百望侠",
      "deliverable": "固定提交的测试记录和 Draft PR",
      "done_when": [
        "负面及正常路径通过，环境和未验证范围清楚，远程保存核验"
      ],
      "status": "done",
      "evidence": [
        "docs/security/evidence/f01-f02/docker-results.json",
        "docs/security/evidence/f01-f02/tests-21ded30.log",
        "docs/security/f01-f02-remediation.md",
        "https://github.com/huangfushaohui8-png/rebucca/pull/2"
      ]
    }
  ]
}
```
<!-- /engineering-meta -->
