# Rebucca 内部回调模块

版本：1.0.1｜日期：2026-10-11｜状态：本轮局部实现及隔离测试通过；真实服务未验收｜责任：百望侠（自检，独立复核待进行）

继承根规格 rebucca.adoption 1.1.0 的业务价值和安全边界，只覆盖 F01/F02 受影响流程；不将整个产品工程化。

使用真实 Django 测试客户端/ORM 和新建临时 SQLite；只替代有启动副作用的 GlobalUtils 与外部媒体/SIP。合成 FFmpeg 测试另行执行；隔离兼容层不能冒充完整服务。

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
  "kind": "test-spec",
  "tests": [
    {
      "id": "TS-001",
      "title": "匿名/Safe/登录会话/远端/转发头/跨身份/未知路由拒绝",
      "requirements": [
        "R-001"
      ],
      "preconditions": "隔离测试设置，无企业数据、无现场网络、无模型",
      "steps": [
        "匿名/Safe/登录会话/远端/转发头/跨身份/未知路由拒绝",
        "断言HTTP状态、无副作用或数据库预期变更；保存日志"
      ],
      "expected": [
        "四个精确 /inner/ 路由强制独立服务凭据；旧 Safe/登录会话均不能绕过",
        "旧上游失败边界复用 2026-10-04 归档证据；本轮固定新版符合拒绝/正常判据"
      ],
      "status": "PASS",
      "evidence": [
        "tests/test_security.py",
        "docs/security/evidence/f01-f02/tests-21ded30.log",
        "docs/security/evidence/f01-f02/docker-results.json",
        "固定代码 21ded3072827a77703824ca2692d00e453e3c4b6"
      ]
    },
    {
      "id": "TS-002",
      "title": "异常JSON/参数、跨对象/跨协议、合法更新/删除/发布/按需邀请验证",
      "requirements": [
        "R-002"
      ],
      "preconditions": "隔离测试设置，无企业数据、无现场网络、无模型",
      "steps": [
        "异常JSON/参数、跨对象/跨协议、合法更新/删除/发布/按需邀请验证",
        "断言HTTP状态、无副作用或数据库预期变更；保存日志"
      ],
      "expected": [
        "SIP只可创建/更新/删除匹配 app=rtp、code=name 的 GB28181(21)流，不改手工拉流/其他协议记录或所有者",
        "旧上游失败边界复用 2026-10-04 归档证据；本轮固定新版符合拒绝/正常判据"
      ],
      "status": "PASS",
      "evidence": [
        "tests/test_security.py",
        "docs/security/evidence/f01-f02/tests-21ded30.log",
        "docs/security/evidence/f01-f02/docker-results.json",
        "固定代码 21ded3072827a77703824ca2692d00e453e3c4b6"
      ]
    },
    {
      "id": "TS-003",
      "title": "SIP发送头与ZLM私有配置生成，不执行附带二进制",
      "requirements": [
        "R-003"
      ],
      "preconditions": "隔离测试设置，无企业数据、无现场网络、无模型",
      "steps": [
        "SIP发送头与ZLM私有配置生成，不执行附带二进制",
        "断言HTTP状态、无副作用或数据库预期变更；保存日志"
      ],
      "expected": [
        "SIP POST请求带独立服务头/凭据，禁止重定向泄露",
        "旧上游失败边界复用 2026-10-04 归档证据；本轮固定新版符合拒绝/正常判据"
      ],
      "status": "PASS",
      "evidence": [
        "tests/test_security.py",
        "docs/security/evidence/f01-f02/tests-21ded30.log",
        "docs/security/evidence/f01-f02/docker-results.json",
        "固定代码 21ded3072827a77703824ca2692d00e453e3c4b6"
      ]
    }
  ]
}
```
<!-- /engineering-meta -->
