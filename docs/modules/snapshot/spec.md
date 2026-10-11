# Rebucca 截图模块

版本：1.0.0｜日期：2026-10-11｜状态：本轮软件试验规格已定版｜责任：百望侠（自检，独立复核待进行）

继承根规格 rebucca.adoption 1.1.0 的业务价值和安全边界，只覆盖 F01/F02 受影响流程；不将整个产品工程化。

输入输出与权限按以下需求执行。失败判据独立于实现；调用真实设备/生产环境不在范围内。

**身份与对象权限：** 无会话/失效用户/旧 Safe 返回 401；普通用户只访问自己流，管理员可访问登记流，非拥有者返回 403，授权前不读缓存/调用 FFmpeg

**安全参数与私有截图执行：** GET app/name 是最多50字符的 ASCII 标识，拒绝空值/重复参数/控制字符/路径与 shell 元字符；force仅0/1；FFmpeg用可信绝对路径、独立 argv、shell=False、超时和非交互执行；RTSP只用服务端回环媒体端口和已登记 app/name；缓存以流 id 分隔，私有目录、禁止 static 根内缓存、原子临时 JPEG、大小限制、并发锁；不读取旧公共截图

**正常截图与失败恢复：** 授权正常请求/缓存/强制刷新可返回 JPEG 与 no-store；超时/失败不暴露命令/内部异常，不返回过期强制刷新结果；合成视频经真实 FFmpeg 形成 JPEG；协议/完整媒体集成另外标 NOT_RUN

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.snapshot",
  "doc_version": "1.0.0",
  "kind": "spec",
  "revision": 1,
  "open_questions": [],
  "requirements": [
    {
      "id": "R-001",
      "title": "身份与对象权限",
      "status": "active",
      "acceptance": [
        "无会话/失效用户/旧 Safe 返回 401；普通用户只访问自己流，管理员可访问登记流，非拥有者返回 403，授权前不读缓存/调用 FFmpeg"
      ]
    },
    {
      "id": "R-002",
      "title": "安全参数与私有截图执行",
      "status": "active",
      "acceptance": [
        "GET app/name 是最多50字符的 ASCII 标识，拒绝空值/重复参数/控制字符/路径与 shell 元字符；force仅0/1",
        "FFmpeg用可信绝对路径、独立 argv、shell=False、超时和非交互执行；RTSP只用服务端回环媒体端口和已登记 app/name",
        "缓存以流 id 分隔，私有目录、禁止 static 根内缓存、原子临时 JPEG、大小限制、并发锁；不读取旧公共截图"
      ]
    },
    {
      "id": "R-003",
      "title": "正常截图与失败恢复",
      "status": "active",
      "acceptance": [
        "授权正常请求/缓存/强制刷新可返回 JPEG 与 no-store；超时/失败不暴露命令/内部异常，不返回过期强制刷新结果",
        "合成视频经真实 FFmpeg 形成 JPEG；协议/完整媒体集成另外标 NOT_RUN"
      ]
    }
  ]
}
```
<!-- /engineering-meta -->
