"""私有快照缓存和无Shell的FFmpeg执行，不导入摄像头/媒体后台。"""
import contextlib
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

from app.security import stream_component

MAX_JPEG_BYTES = 4 * 1024 * 1024


def local_rtsp_url(app, name, port):
    """截图仅连接本机ZLM；不使用浏览器参数或外部host作为网络目的地。"""
    app, name = stream_component(app), stream_component(name)
    if isinstance(port, bool) or not 1 <= int(port) <= 65535:
        raise ValueError("invalid media port")
    return "rtsp://127.0.0.1:%d/%s/%s" % (int(port), quote(app, safe=""), quote(name, safe=""))


def read_jpeg(path):
    """有限读取普通文件，拒绝软链接、过大的产物和非JPEG字节。"""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or not 100 < info.st_size <= MAX_JPEG_BYTES:
            return None
        data = file.read(MAX_JPEG_BYTES + 1)
    return data if data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9") else None


@contextlib.contextmanager
def snapshot_lock(path):
    """跨进程的非阻塞每流锁；并发刷新返回忙碌，崩溃后由OS释放锁。"""
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                acquired = True
            except OSError:
                pass
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                pass
        yield acquired
    finally:
        if acquired and os.name == "nt":
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        os.close(fd)


def capture_jpeg(rtsp_url, snap_path, ffmpeg_cmd):
    """以独立argv在12秒内取一帧，校验后原子发布；失败不覆盖旧缓存。"""
    executable = Path(ffmpeg_cmd)
    if (not executable.is_absolute() or not executable.is_file()
            or executable.suffix.lower() in (".bat", ".cmd") or not os.access(executable, os.X_OK)):
        raise ValueError("trusted FFmpeg executable unavailable")
    with tempfile.NamedTemporaryFile(prefix="snap-", suffix=".jpg",
                                     dir=Path(snap_path).parent, delete=False) as file:
        temporary = file.name
    try:
        result = subprocess.run(
            [str(executable), "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp",
             "-timeout", "5000000", "-i", rtsp_url, "-frames:v", "1", "-f", "image2",
             "-update", "1", "-y", temporary],
            shell=False, timeout=12, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        data = read_jpeg(temporary) if result.returncode == 0 else None
        if data:
            os.chmod(temporary, 0o600)
            os.replace(temporary, snap_path)
        return data
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
