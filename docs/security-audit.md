# Rebucca 源码引入与安全审计

日期：2026-10-04｜审查者：百望侠｜审计对象：v1.005，提交 `8440b5545fc4f02bad105cbcc1ed09f24a0a2dfd`。

**结论：有复用价值，但原版未通过上线安全准入。已确认严重输入和权限边界问题；本次未发现足以认定为蓄意恶意后门的源码证据，也不能证明无后门。** 随附二进制、模型和浏览器解码器未执行、未做完整逆向或动态网络分析。

用户副本：[huangfushaohui8-png/rebucca](https://github.com/huangfushaohui8-png/rebucca)。截图中的 `beixiaocai/rebucca` 当前重定向到 [yuturuishi/rebucca](https://github.com/yuturuishi/rebucca)。已保留上游历史、全部 166 个受管文件及 MIT LICENSE。副本为公开 fork；本次只增加审计、工程与部署文档，没有修复或部署产品源码。

## 核验方式与覆盖

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| 源码语法 | 76 个 Python 文件解析通过 | 没有导入并启动完整应用 |
| Bandit 1.9.4 | 16,386 行，209 条原始提示：高 7、中 23、低 179；无解析错误 | 提示需手工判定，不等于 209 个真实漏洞 |
| pip-audit 2.10.1 | 12 个固定直接依赖，99 行公告记录，去重后 57 组，涉及 4 个包 | 4 个浮动依赖、全部间接依赖、系统库未覆盖；不是 57 项都可被此系统利用 |
| 隔离数据流验证 | 8 个证据检查完成，所测原版安全边界均失败 | 使用合成请求、内存 SQLite、临时文件与服务替身；没有真实 HTTP、shell 执行或现场破坏 |
| 文件来源 | 原始文件清单、41 项二进制/模型/相关资产 SHA256 已登记 | 校验值固定字节，不能证明来源可信或没有后门 |
| 人工重点审阅 | 认证/角色、内部回调、系统命令、SQL、上传/下载、模型加载、版本外联、日志、启动生命周期 | 不是逐行形式化证明或独立第三方复核 |
| 运行验收 | `NOT_RUN` | 未加载 `.pt`、未运行附带 ZLM、未启动 Docker 应用、未连接真实摄像头、未抓包 |

覆盖入口：`framework/settings.py`、`framework/urls.py`、`app/middleware.py`、`app/urls.py`、`ViewsBase/User/Stream/Nvr/Storage/System/Innerl/LLM/SmallModel/VersionView`、`GlobalUtils/Config/Database/ZLMediaKitApi/GB28181SipServer/LLMUtils/MediaServerManager`、推理引擎、录像进程、启动和相关模板。AI 识别效果、所有业务规则算法和端到端性能未做验收。

原始结果及版本信息见 [证据目录](security/evidence/)，复核脚本见 [isolate_checks.py](security/tools/isolate_checks.py)。脚本只运行已审阅的函数定义，拦截命令执行和真实删除，不启动全应用。脚本复现成功表示证据成立，**不表示产品安全通过**。

## 必须处理的发现

严重度按此系统的可达性和影响评估；未发布 CVSS 分数。以下源文件定位均对应固定上游提交，不对应未来变更。

### F01 — 严重：匿名截图接口的命令注入与截图泄露

- `app/middleware.py` 将 `/nvr/openSnap` 放入免登录白名单。
- `app/views/NvrView.py:321–359` 不检查身份，直接取 `app/name`；缓存图片也直接返回。
- `app/utils/ZLMediaKitApi.py:55–61` 把原始 `app/name` 拼入 RTSP URL。
- `NvrView.py:304–312` 将 URL 放入双引号字符串，调用 `subprocess.run(..., shell=True)`。用于缓存文件名的清理没有保护进入 URL 的原始输入；双引号不能阻止 shell 命令替换。
- 隔离试验确认匿名输入到达 shell 字符串，且缓存截图无需登录即可读取。没有执行恶意命令或通过网络攻击服务器。

**处置：** 恢复登录及摄像头对象权限，严格约束 app/name，使用参数数组和 `shell=False`，固定可信 FFmpeg 路径，并加入负面输入、并发/频率和缓存访问测试。仅修改默认密码不能解决此问题。

### F02 — 高：内部回调无鉴权，可改写和删除视频记录

`app/middleware.py` 对整个 `/inner/` 前缀直接放行；`OPEN_API_SAFE_HEADER_PREFIXES` 虽有声明，实际没有强制使用。`app/urls.py:73–76` 对回调免 CSRF，`InnerlView.py:31–187` 的更新/删除方法未校验调用方。隔离试验在无会话、无 Safe 的情况下到达记录删除路径。

**处置：** 内部接口独立监听并限制网络；服务身份鉴权、重放防护和对象校验在服务端执行。ZLM 回调、SIP 服务与 Web 管理权限分开。生产反向代理拒绝外部 `/inner/`，底层监听端口仍须受防火墙保护。

### F03 — 高：公开默认凭据与固定安全密钥

`config.json` 固定 Safe、ZLM API secret、弱 SIP 口令；`framework/settings.py` 固定 Django SECRET_KEY。随附 SQLite 有 2 个启用用户，且管理员密码哈希与 README 所写默认密码匹配。固定 Safe 被多个 open API 当作身份依据；公开值不构成秘密。仓库示例配置与数据库不能直接成为生产状态。

**处置：** 新环境生成独立随机密钥；设置唯一强管理员口令，停用样例账号，清空导入会话，换 SIP 凭据；配置与用户数据库从 Git 分离。Django 秘钥泄露的具体影响取决于会话后端等条件，本审计没有把它直接等同于伪造任意数据库会话。

### F04 — 高：普通登录用户可以修改管理员

`ViewsBase.py:104–120` 只判断是否有用户 ID；`UserView.py:240–320` 修改用户时未要求管理员身份或限制目标账户。`UserView.py` 的登录代码明确让所有登录用户访问全部功能。隔离试验以非超级用户合成会话到达管理员的改密码与保存路径。

此外，`UserView.api_openIndex` 使用 `select * from auth_user`，响应包含密码哈希，而非只包含可显示字段。

**处置：** 服务端落实管理员/运维/只读角色及对象权限；管理员账号管理不得用通用 Safe token 授权；响应显式列字段，禁止输出密码哈希；变更权限和停用后使旧会话失效。

### F05 — 高：多处 SQL 字符串拼接

`StreamView.py:216、257、570–584` 将外部 code/app/name/search_text 放入 SQL；`UserView.py:292` 对用户名也直接拼接。`Database.py` 执行完整字符串，没有参数化接口。隔离内存数据库试验确认外部 code 可以改变筛选语义并返回本不匹配的摄像头记录。

**处置：** 优先使用 Django ORM，否则统一参数化查询；保留正常查询与负面字符串的独立预期。没有测试堆叠语句或声称已读取真实用户数据。

### F06 — 高：下载路径越界，并会计划删除越界文件

`StorageView.py:35–80` 只检查后缀，然后 `os.path.join(storageTempDir, filename)`；缺少绝对路径、`..` 和真实路径包含性检查。读取后还启动线程删除该路径。隔离临时文件试验确认可读取指定目录之外的样例 `.jpg`，并到达计划删除路径。真实删除线程被拦截。

影响受应用文件权限和允许后缀限制，不能表述为读取任意扩展名。该接口仍有全局中间件，但任意登录用户及知悉默认 Safe 的请求可能进入。

**处置：** 文件 ID 映射到服务端允许目录，校验 `realpath` 和符号链接，落实所有权；下载不能依用户输入路径触发删除；独立受控任务回收临时文件。

### F07 — 高：凭据被广泛返回或记录

`LLMView.py:64–94、218–225` 明文返回 API key；系统配置接口返回敏感字段；`GlobalUtils.py:46–47` 记录整个配置；系统保存和用户创建/改密码路径记录请求参数；`GB28181SipServer.py:1772` 会在调试日志中打印 SIP 密码。视频 URL 也可能包含摄像头用户名/口令。导出日志将配置与日志打包。

随附 SQLite 存在 1 个非空模型 API key 字段，未验证是否有效，未在报告复印其值；生产初始化必须清理此类样例配置。

**处置：** 秘密仅在受控运行配置中保存；接口只返回掩码和配置状态；日志与导出统一脱敏，限制管理员访问和保留周期。

### F08 — 高：生产配置硬编码为调试状态

`framework/settings.py` 固定 `DEBUG=True`、`ALLOWED_HOSTS=['*']`，并用开发静态服务提供资源；允许所有 iframe 嵌入。`config.json.logDebug=false` 只影响日志，不会关闭 Django DEBUG。默认没有 HTTPS 安全 Cookie 等完整生产配置。

**处置：** 单独生产设置、受控 HOST、随机 SECRET_KEY、HTTPS/Cookie/CSRF/点击劫持防护；用适用静态服务托管公共资源。执行 Django 部署检查与真实反向代理验收。

### F09 — 中：版本检查明文发送主机与访问元数据

`GlobalUtils.CheckServerUtils.checkVersion` 向 `http://www.yuturuishi.com/api/rebucca/checkVersion` POST 主机名、CPU、系统信息、请求/访问 IP、端口、启动时间等。主页和版本页触发检查；`isEnableUpdatePopup` 是发送数据中的标志，函数没有因其为 false 就停止请求。

最新提交已移除 Python 周期性心跳代码，不能沿用旧版本称“仍每隔一段时间心跳”。本次读取的版本检查请求体未包含视频、录像或账户口令。LLM 图片外发属于另外一条可选业务链路。

**处置：** 默认关闭版本外联并有明确数据说明；必要更新服务用 HTTPS、最少字段、校验响应。运行网络默认拒绝，审核后放行指定服务。

### F10 — 高：外部版本响应未经转义进入页面 HTML

`templates/app/version/index.html:294–334` 将版本说明、消息和下载 URL 拼接到 `innerHTML`。响应来自前述明文 HTTP 外联；作者服务或传输链路被控制时，可能向登录用户页面注入 HTML/脚本或危险链接。该项由源码确认危险渲染路径，未启动浏览器执行攻击。

**处置：** 使用 `textContent` 或可靠上下文转义、下载 URL 的协议/域名白名单、CSP 和 HTTPS；关闭外联作为隔离期间的补充控制。

### F11 — 高风险依赖需要升级：4 个包命中 57 组去重公告

| 固定依赖 | 去重公告组 | 处理方向 |
| --- | ---: | --- |
| Django 5.0.4 | 27 | 5.0 系列已停止支持；迁移到受支持的 5.2 LTS 最新安全修订并实测 |
| requests 2.28.2 | 4 | 升级受维护修订，验证重定向、代理和凭据处理 |
| Pillow 9.5.0 | 19 | 升级，复测图片/验证码处理与资源限制 |
| cryptography 46.0.4 | 7 | 使用不受已检索公告影响的受维护版本，复核实际调用 |

99 行原始记录有重复 ID/别名，按包内公告身份去重为 57 组。完整 ID、修复版本和描述见 `dependency-summary.json`。公告命中是版本层风险，是否可利用取决于调用路径、平台和数据。不能简单升到某条公告的最低修复版本就认为解决全部问题。

`torch/ultralytics/openai/openvino` 使用 `>=`，没有已解析锁文件；全部间接依赖与原生库也未进行完整漏洞检索。生产需要完整环境解析、锁版本和哈希，再扫描完整依赖图。

### F12 — 高：不可信模型与运行时远程代码信任

小模型上传允许 `.pt/.engine/.model` 等，基本只检查后缀；推理代码会加载用户指定文件。PyTorch 官方将不可信模型视作不可信程序。`pytorch_engine.py:103` 回退 `torch.hub.load('ultralytics/yolov5', ... trust_repo=True)`，未固定仓库提交，可能下载并执行上游代码。

随附 `.pt` 只用 `pickletools` 解析指令，不反序列化；所见全局引用与 YOLO 网络一致，没有因此认定恶意，也不证明权重没有后门或数据投毒。

**处置：** 模型由受限管理员导入、带来源/许可/摘要和复核；禁止运行时 torch.hub 远程加载；低权限隔离推理；按需求选择安全格式及可追溯模型。改成 ONNX 不自动消除解析器漏洞、模型投毒或原有许可义务。

### F13 — 中，未核清：附带二进制与浏览器播放器的供应链

Linux ZLM 为 x86_64/aarch64 ELF；`version.txt` 只标“2025/05/11 master”，没有可复现的完整源提交、构建记录或签名。附带 OpenSSL 字符串为 `1.1.1f 31 Mar 2020`，实际安全修补状态未验证。播放器有压缩 JavaScript 和 WebAssembly，没有随附完整构建来源；静态字符串含第三方 CDN URL，是否在选定功能触发未动态验证。

ZLM 二进制中有 `http://report.zlmediakit.com:8888/index/api/reporecv` 字符串。官方 CMake 存在 `DISABLE_REPORT`，默认 OFF。字符串是报告功能的线索，不能仅凭它认定本二进制实际发包或恶意后门。

**处置：** 从审查过的官方源码固定提交重建 ZLM，并核验 `-DDISABLE_REPORT=ON`、安全系统依赖和包清单；记录适配差异、镜像摘要与抓包结果。GB28181/定制 API 兼容性必须复测，不能假设任意新版镜像都兼容本项目。

### F14 — 中：业务文件位于免登录静态目录

截图、录像和上传权重位于 `static/storage`、`static/upload`。中间件对 `/static/` 放行，DEBUG 静态服务可直接暴露已知路径资源。只保护管理界面不足以保护业务文件。

**处置：** 业务文件移到非公开持久卷，通过用户/摄像头权限或短时签名提供读取；公共 static 只含界面资源。

### F15 — 中：资源耗尽、URL 请求和 CSRF 的边界不足

请求体上限 1.5GB，上传缺少统一硬大小限制与内容校验；截图可频繁触发 FFmpeg；多处分页/列表无严格上限。登录错误会持久停用目标账号，需评估可被恶意锁定的风险。模型测试 `/llm/openTest` 免 CSRF，且可提交任意 API base URL；视频接入也接受 URL。缺少统一的协议/目标网段/费用约束，形成内网探测、数据发往错误模型端点和资源消耗的风险。SameSite Cookie 可缓解部分跨站 POST，不取代 CSRF 和服务端目标校验。

**处置：** 摄像头网段及批准模型端点白名单、出站策略、CSRF、登录/推理/上传/截图限流、超时、大小与队列上限；资源与费用超限明确失败和降级。

## 外联与后门判断

| 路径 | 数据/行为 | 当前证据 | 生产建议 |
| --- | --- | --- | --- |
| 作者版本 API | 主机与访问元数据，明文 HTTP | 已审阅实际请求体及前端触发；当前版无旧周期心跳 | 默认禁用，审核后仅限必要字段 |
| 可选 OpenAI 兼容接口 | 报警截图/测试图片和提示词 | `LLMUtils.infer` 明确编码图片并发送至配置地址 | 首期本地处理；外发单独确认数据范围并限制端点 |
| torch.hub | 回退时加载远程 YOLOv5 仓库 | 源码 `trust_repo=True`、未锁提交 | 取消运行时下载与执行 |
| ZLM 报告地址 | 可能的组件遥测 | 二进制字符串与官方编译选项；未抓包 | 固定源码重建、关闭报告并动态验证 |
| 播放器 CDN | 可能下载特定辅助脚本/资产 | 压缩 JS 字符串线索 | 核清版本、许可、功能触发并自托管所需资产 |
| 摄像头/ZLM/SIP | 现场视频接入与回调 | 正常功能用途，但鉴权/网络边界不足 | 设备 VLAN、最小协议/端口放行 |

未在已审阅源码中识别到矿工、反向 shell、外部隐藏管理员、自动植入持久化或将全部录像偷传的明确证据。代码存在公开固定凭据、危险可达执行路径和遥测，必须处理，但不能仅凭这些判断作者恶意。**“尚未发现明确恶意后门”不等于“已排除后门”。** 模型行为后门、依赖投毒、预编译程序和浏览器解码器仍需后续溯源与隔离动态分析。

## 许可证与商用边界

平台顶层源代码许可证为 MIT，须保留相应版权和许可声明。最新上游 README 已另行注明 Ultralytics 为 AGPL-3.0、模型权重有独立许可，不能把宣传“MIT 免费商用”扩展为所有组合都允许闭源免费商用。

使用 ONNX Runtime/OpenVINO 是推理引擎选择；将 YOLO 权重转换成 ONNX 不会改变权重原来的许可。闭源、私有部署或商用集成需按实际组件、模型来源和组合核验许可；可选受允许许可的模型或相应商业许可。EasyPlayer Pro/解码器的具体版本、商业使用和再分发证明本次未核清，列为生产准入缺口，不照搬其他同名仓库许可证。

## 上线准入与当前状态

- F01/F02/F03/F04/F05/F06/F07/F08 的权限、输入和秘密边界必须有修复及负面回归；F09/F10 默认关闭外联并完成安全处理。
- F11 完整锁定并扫描依赖，F12 限制模型与远程加载，F13 核清程序/播放器来源与构建，F14 移出业务静态文件，F15 设置资源与访问边界。
- 生产验证还包括断流恢复、报警证据、重启/持久化、备份恢复、录像留存、TLS/角色/网络策略、真实模型效果和目标硬件容量。
- 当前产品安全准入：`FAIL`；实际部署、完整 HTTP/浏览器复测、动态外联、AI 效果：`NOT_RUN`。本期引入与审计材料可交付，整改和生产验收不能据此标记完成。

详细执行顺序见 [部署方案](deployment-plan.md)。

## 一手参考资料

核验日期 2026-10-04；实际审计版本以证据目录固定 SHA 为准。

1. [上游固定源码](https://github.com/yuturuishi/rebucca/tree/8440b5545fc4f02bad105cbcc1ed09f24a0a2dfd) 与 [LICENSE](https://github.com/yuturuishi/rebucca/blob/8440b5545fc4f02bad105cbcc1ed09f24a0a2dfd/LICENSE)。
2. [Django 支持版本](https://www.djangoproject.com/download/) 与 [生产部署检查](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)。
3. [PyTorch Security Policy](https://github.com/pytorch/pytorch/security/policy)。
4. [Ultralytics 许可说明](https://www.ultralytics.com/license)。
5. [ZLMediaKit 官方 CMake](https://github.com/ZLMediaKit/ZLMediaKit/blob/master/CMakeLists.txt)，本次获取该文件 blob SHA `11cf65282ae7cd38a3d03ce16f960d5b4c67b990`，`DISABLE_REPORT` 默认 OFF。
6. [Bandit](https://github.com/PyCQA/bandit)、[pip-audit](https://github.com/pypa/pip-audit)。公开公告版本风险的机器检索结果保留在本仓库，未验证每条公告在本应用中的可利用性。
