# Rebucca F01/F02 安全整改与复现

日期：2026-10-11。基础 main：`42a0e0baebf7d48cc7a752570386112ae1b6b394`。本轮仅局部修复；产品生产安全准入仍 **FAIL**。

固定已测试代码：[21ded3072827a77703824ca2692d00e453e3c4b6](https://github.com/huangfushaohui8-png/rebucca/commit/21ded3072827a77703824ca2692d00e453e3c4b6)。交付：[Draft PR #2](https://github.com/huangfushaohui8-png/rebucca/pull/2)，分支 `security/f01-f02-20261011`；后续证据提交只更新文档和日志，不改变上述测试代码。

## 已执行验证

| 层次 | 结果与证据 | 实际覆盖 |
| --- | --- | --- |
| 源码检查 | AST 85 文件通过；[源文件摘要](evidence/f01-f02/source-manifest.json) | 作者审阅身份、对象、参数和执行边界；沿用原审计，没有重做整产品审计 |
| 本地隔离 Django | 50 PASS、1 SKIP；[检查摘要](evidence/f01-f02/local-checks.json)、[日志](evidence/f01-f02/local-tests.log) | 真实测试客户端、中间件、目标视图及 ORM；新建内存库，替代 GlobalUtils 和媒体/SIP 副作用 |
| 主机 Docker 隔离 Linux | 51/51 PASS，退出码 0；[容器记录](evidence/f01-f02/docker-results.json)、[日志](evidence/f01-f02/tests-21ded30.log) | 含回环合成 H264 RTSP 与真实 FFmpeg 取帧；无外网、只读、非 root、无能力/端口/宿主挂载；容器已停止并移除 |
| 真实产品服务 | NOT_RUN；[范围与门禁](evidence/f01-f02/review-summary.json) | 原生 ZLM/SIP、完整 HTTP 服务生命周期、Windows、生产摄像头/数据库均未验证 |
| 独立复核及生产准入 | NOT_RUN / FAIL | 局部隔离 PASS 不构成整体产品安全、部署完成或合并许可 |

容器实际 Python 3.12.15、FFmpeg 5.1.9（Debian `7:5.1.9-0+deb12u1`），Docker 29.7.2、Linux amd64；[环境记录](evidence/f01-f02/runtime-21ded30.log)。固定测试镜像 ID 为 `sha256:490f0bbdfd1e3af2e07a96534d0f41f2a30539c64e4acfc992bf4cf73a65ef95`，[构建日志](evidence/f01-f02/build-corrected.log)已保存。其依赖版本复用产品依赖用于兼容测试，不代表已消除原依赖漏洞。

首次候选 `b18f24f4abed762932daf962736b5181cb67b7e4` 的容器运行出现 2 ERROR、1 FAIL，未计为通过：[失败记录](evidence/f01-f02/initial-failure.json)、[原始日志](evidence/f01-f02/tests-b18f.log)。原因分别是 `/tmp` noexec 拒绝测试假执行文件，以及实际 FFmpeg RTSP demuxer 不接受 `-rw_timeout`。已保留 noexec、改用已安装执行文件的元数据作为 subprocess 替身，并将取帧参数改为支持的 `-timeout 5000000`；修正提交完整重跑后通过。

回归覆盖匿名/失效会话/旧 Safe、伪造管理员及角色撤销、跨用户和缓存读取、未知/重复对象、恶意标识和重复查询、超时/失败/并发/软链接、正常所有者/管理员及 force；回调覆盖匿名/网页会话/跨服务 token、缺失或共用秘密、远端或代理头、方法/路由/JSON 边界、跨协议修改与删除、正常更新/删除/发布/按需邀请，以及实际 SIP 发送函数和 ZLM 私有配置生成。具体用例在 [tests/test_security.py](../../tests/test_security.py)。旧失败边界复用 [2026-10-04 证据](evidence/isolated-findings.json)，未重新连接设备复现。

## 最终行为与兼容边界

- 截图沿用 GET `/nvr/openSnap?app=live&name=camera1`、JPEG 与 no-store。数据库当前有效用户才能访问；普通用户仅自己的流，管理员访问登记流。身份与对象权限在缓存之前校验；旧Safe不能授权。app/name最多50字符，限定ASCII字母/数字开头及后续字母/数字/点/短横线/下划线；重复参数与异常force拒绝。
- 快照连接回环ZLM端口，用户输入和config.host不能指定外部目的地。FFmpeg来自环境指定的绝对可信路径，以独立argv、shell=False和12秒超时执行；短时无帧最多再试一次。缓存移到BASE_DIR/var/snapshots，用流id隔离、跨进程OS锁、临时JPEG及原子替换；最多4MiB。旧static中的其他截图/报警文件未迁移，F14仍待修。
- 四个内部回调只有POST JSON（64KiB内）可用。中间件与视图都验证服务身份，真实REMOTE_ADDR必须是回环，不信任/接受代理转发头。SIP只能更新/删除匹配的GB28181流，ZLM只能更新匹配的被动推流；不能覆盖手工源或改变拥有者，重复编号失败关闭。
- 独立token从 `REBUCCA_SIP_CALLBACK_TOKEN`、`REBUCCA_ZLM_CALLBACK_TOKEN` 读取，必须是不同的64位小写十六进制（各32随机字节）。缺失、格式错误、相同、旧Safe、网页会话或跨服务身份均不能授权。SIP用 `X-Rebucca-Service: sip` 与 `Authorization: Bearer ...`；禁止重定向。
- 原生ZLM两个hook接受专用URL查询token。MediaServerManager启动时从原INI生成0600私有临时配置，并替换hook URL；保留GBK模板的大小写键与媒体值。源文件、命令日志和仓库不写入运行token。外部自行启动ZLM必须使用相同的运行配置生成器；既有已运行ZLM不会自动刷新hook，必须在后续获准试验中重启并验证。

## 可复现隔离入口

开发环境（Python 3.10+）：

```bash
python3 -m venv /tmp/rebucca-test-venv
/tmp/rebucca-test-venv/bin/pip install -r tests/requirements-security.txt
/tmp/rebucca-test-venv/bin/python -m tests.run_security
```

默认跳过仅容器允许的合成RTSP用例。新建内存SQLite、合成账户/token与临时目录；不打开rebucca.sqlite3，不导入GlobalUtils网络/线程初始化，不加载其他产品视图。真实中间件、NvrView、InnerlView、ViewsBase和ORM参与测试；媒体/设备副作用通过明示替身验证。

Docker：

```bash
# 使用新的隔离 checkout，固定到上面的已测试代码提交，再构建。
docker build -f Dockerfile.security-test -t rebucca-security-test:candidate .
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user 65534:65534 \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m --pids-limit 128 \
  --cpus 2 --memory 512m rebucca-security-test:candidate
```

不使用-p、不使用宿主目录/设备/Docker socket挂载，容器只在回环运行短时合成H264 RTSP fixture，真实FFmpeg取帧经真实授权截图视图返回JPEG。构建阶段下载官方Python基础层、Debian FFmpeg及固定测试Python依赖；运行期无外网。测试镜像有意不复制示例数据库、附带ZLM二进制/共享库、权重或播放器；**不是可生产部署的完整产品镜像**。基础镜像已锁digest，apt包版本及镜像ID按实测证据记录；未达到整产品供应链准入。

## 密钥与访问部署条件（尚未启用）

在隔离试验环境由运维分别生成 `secrets.token_hex(32)`，将两值放受限运行环境，禁止复制到源码、Git、config.json、截图、错误或访问日志。新快照默认私有var目录；如配置REBUCCA_SNAPSHOT_DIR或REBUCCA_PRIVATE_RUNTIME_DIR，禁止放到任何公开静态映射。FFmpeg默认Linux `/usr/bin/ffmpeg`，Windows须显式设置可信exe绝对路径；Windows锁实现未在本轮容器验收。

管理入口的反向代理必须拒绝 `/inner/`，内部回调共享本机网络空间；不能去掉转发头检查来让公网代理回调可用，也不能为拆容器扩大成任意内网IP放行。ZLM hook token可重放且含于URL，必须不记录查询参数、不对其他角色暴露生成配置，并轮换运行秘密。现有产品runserver/DEBUG日志不能当作安全生产入口。签名、重放/幂等和独立内部监听是后续门禁，不能用本轮Bearer身份声称完成。

## 回退

本轮不迁移业务数据库，也不写企业数据。独立分支/PR可以关闭，未部署时保留main不变。若后续私有试验不通过，停止该试验容器并保全临时验证日志，撤销/轮换试验服务token，删除生成的私有runtime INI；不要公开历史快照或退回匿名截图/无鉴权callback。已合并补丁只能通过新的revert PR回退，不能force-reset共享历史。旧main带已知严重漏洞，不是可恢复为生产的安全版本；安全回退目标是停服隔离。

## 保留门禁

F03–F15、固定默认SECRET_KEY/凭据、角色/SQL/文件边界、静态业务文件、完整依赖与二进制来源、遥测/外联、真实ZLM/SIP/摄像头与数据库、完整产品启动生命周期均保留原 FAIL/NOT_RUN。作者自检与主机隔离运行不等于独立安全复核。独立复核、真实媒体组件握手和上述门禁满足前，本PR保持Draft；不合并、不上线、不开放公网端口。

执行证据已保存于 [evidence/f01-f02/](evidence/f01-f02/)，分别标明本地检查、隔离容器测试、修正前失败和真实服务未验证项。GitHub PR 后续仅证据/文档提交不改变已测试代码；固定代码摘要用于核验这一点。
