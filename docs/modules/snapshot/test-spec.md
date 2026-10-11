# Rebucca 截图模块

版本：1.0.0｜日期：2026-10-11｜状态：本轮软件试验规格已定版｜责任：百望侠（自检，独立复核待进行）

继承根规格 rebucca.adoption 1.1.0 的业务价值和安全边界，只覆盖 F01/F02 受影响流程；不将整个产品工程化。

使用真实 Django 测试客户端/ORM 和新建临时 SQLite；只替代有启动副作用的 GlobalUtils 与外部媒体/SIP。合成 FFmpeg 测试另行执行；隔离兼容层不能冒充完整服务。

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.snapshot",
  "doc_version": "1.0.0",
  "spec_revision": 1,
  "spec_doc_version": "1.0.0",
  "spec_sha256": "21e3b162452528781dce7a2d399057cd568248e706d557d1cf7595555b2b9d21",
  "kind": "test-spec",
  "tests": [
    {
      "id": "TS-001",
      "title": "匿名/失效会话/伪造管理员/Safe/跨对象/公共缓存访问拒绝",
      "requirements": [
        "R-001"
      ],
      "preconditions": "隔离测试设置，无企业数据、无现场网络、无模型",
      "steps": [
        "匿名/失效会话/伪造管理员/Safe/跨对象/公共缓存访问拒绝",
        "断言HTTP状态、无副作用或数据库预期变更；保存日志"
      ],
      "expected": [
        "无会话/失效用户/旧 Safe 返回 401；普通用户只访问自己流，管理员可访问登记流，非拥有者返回 403，授权前不读缓存/调用 FFmpeg",
        "旧上游存在失败复现，新版符合拒绝/正常判据"
      ],
      "status": "NOT_RUN",
      "evidence": []
    },
    {
      "id": "TS-002",
      "title": "异常查询、文件边界、并发、超时与失败拒绝",
      "requirements": [
        "R-002"
      ],
      "preconditions": "隔离测试设置，无企业数据、无现场网络、无模型",
      "steps": [
        "异常查询、文件边界、并发、超时与失败拒绝",
        "断言HTTP状态、无副作用或数据库预期变更；保存日志"
      ],
      "expected": [
        "GET app/name 是最多50字符的 ASCII 标识，拒绝空值/重复参数/控制字符/路径与 shell 元字符；force仅0/1",
        "旧上游存在失败复现，新版符合拒绝/正常判据"
      ],
      "status": "NOT_RUN",
      "evidence": []
    },
    {
      "id": "TS-003",
      "title": "有效所有者/管理员、缓存/force、合成 FFmpeg JPEG 正常",
      "requirements": [
        "R-003"
      ],
      "preconditions": "隔离测试设置，无企业数据、无现场网络、无模型",
      "steps": [
        "有效所有者/管理员、缓存/force、合成 FFmpeg JPEG 正常",
        "断言HTTP状态、无副作用或数据库预期变更；保存日志"
      ],
      "expected": [
        "授权正常请求/缓存/强制刷新可返回 JPEG 与 no-store；超时/失败不暴露命令/内部异常，不返回过期强制刷新结果",
        "旧上游存在失败复现，新版符合拒绝/正常判据"
      ],
      "status": "NOT_RUN",
      "evidence": []
    }
  ]
}
```
<!-- /engineering-meta -->
