# Rebucca F01/F02 安全整改与复现

日期：2026-10-11。基础 main：`42a0e0baebf7d48cc7a752570386112ae1b6b394`。本轮仅局部修复；产品生产安全准入仍 **FAIL**。

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

执行证据将在固定代码提交后记录于本目录 evidence/f01-f02/，分别标明本地检查、容器测试和真实服务验证。
