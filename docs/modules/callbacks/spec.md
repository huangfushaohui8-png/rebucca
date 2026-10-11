# Rebucca 内部回调模块

版本：1.0.0｜日期：2026-10-11｜状态：本轮软件试验规格已定版｜责任：百望侠（自检，独立复核待进行）

继承根规格 rebucca.adoption 1.1.0 的业务价值和安全边界，只覆盖 F01/F02 受影响流程；不将整个产品工程化。

输入输出与权限按以下需求执行。失败判据独立于实现；调用真实设备/生产环境不在范围内。

**服务身份和入口边界：** 四个精确 /inner/ 路由强制独立服务凭据；旧 Safe/登录会话均不能绕过；只允 POST JSON、<=64KiB；仅回环实际对端、拒绝转发头/未知路由/跨服务调用；视图自身也强制鉴权；token只能来自环境变量：各64位十六进制且SIP/ZLM不同；缺失/错误配置失败关闭，不硬编码秘密

**回调对象边界与安全输入：** SIP只可创建/更新/删除匹配 app=rtp、code=name 的 GB28181(21)流，不改手工拉流/其他协议记录或所有者；ZLM只可更新匹配 app=live 的被动 RTSP/RTMP 流；找不到事件只邀请匹配的 GB28181通道；拒绝非法JSON、非对象、异常标识/类型/端口/时间/设备地址，保持拒绝前无数据库和SIP副作用

**调用方兼容与回归：** SIP POST请求带独立服务头/凭据，禁止重定向泄露；ZLM启动从原配置生成0600私有运行时hook配置，自动注入专用token；原始配置不含运行token；缺失token不启动进程；合成JSON客户端验证四个正常回调；不执行附带媒体二进制/模型，真实组件握手及重放防护保留待验收

<!-- engineering-meta -->
```json
{
  "schema_version": 1,
  "project_id": "yy-rebucca",
  "scope_id": "rebucca.callbacks",
  "doc_version": "1.0.0",
  "kind": "spec",
  "revision": 1,
  "open_questions": [],
  "requirements": [
    {
      "id": "R-001",
      "title": "服务身份和入口边界",
      "status": "active",
      "acceptance": [
        "四个精确 /inner/ 路由强制独立服务凭据；旧 Safe/登录会话均不能绕过",
        "只允 POST JSON、<=64KiB；仅回环实际对端、拒绝转发头/未知路由/跨服务调用；视图自身也强制鉴权",
        "token只能来自环境变量：各64位十六进制且SIP/ZLM不同；缺失/错误配置失败关闭，不硬编码秘密"
      ]
    },
    {
      "id": "R-002",
      "title": "回调对象边界与安全输入",
      "status": "active",
      "acceptance": [
        "SIP只可创建/更新/删除匹配 app=rtp、code=name 的 GB28181(21)流，不改手工拉流/其他协议记录或所有者",
        "ZLM只可更新匹配 app=live 的被动 RTSP/RTMP 流；找不到事件只邀请匹配的 GB28181通道",
        "拒绝非法JSON、非对象、异常标识/类型/端口/时间/设备地址，保持拒绝前无数据库和SIP副作用"
      ]
    },
    {
      "id": "R-003",
      "title": "调用方兼容与回归",
      "status": "active",
      "acceptance": [
        "SIP POST请求带独立服务头/凭据，禁止重定向泄露",
        "ZLM启动从原配置生成0600私有运行时hook配置，自动注入专用token；原始配置不含运行token；缺失token不启动进程",
        "合成JSON客户端验证四个正常回调；不执行附带媒体二进制/模型，真实组件握手及重放防护保留待验收"
      ]
    }
  ]
}
```
<!-- /engineering-meta -->
