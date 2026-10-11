"""最小只读合成RTSP fixture：回环TCP/H264，不支持摄像头接入或外联。"""
import base64
import re
import socket
import struct
import subprocess
import tempfile
import threading
import time
from pathlib import Path


class SyntheticRTSP:
    """仅测试容器使用：生成160x120测试画面，以RTSP interleaved RTP输出。"""
    def __init__(self):
        """所有数据与监听均属于测试，不挂载或读取企业视频。"""
        self._stop = threading.Event()
        self._socket = None
        self._thread = None
        self._connection = None

    def __enter__(self):
        """使用系统FFmpeg合成一帧H264，然后绑定容器回环固定媒体端口。"""
        with tempfile.TemporaryDirectory(prefix="synthetic-video-") as directory:
            video = Path(directory) / "frame.h264"
            subprocess.run(
                ["/usr/bin/ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i",
                 "testsrc2=size=160x120:rate=5", "-frames:v", "1", "-c:v", "libx264", "-threads", "1",
                 "-preset", "ultrafast", "-tune", "zerolatency", "-g", "1", "-f", "h264", str(video)],
                shell=False, check=True, timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self._nals = [n for n in re.split(b"\x00\x00\x00\x01|\x00\x00\x01", video.read_bytes()) if n]
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 10554))
        self._socket.listen(1)
        self._socket.settimeout(0.2)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args):
        """停止短时fixture并释放监听，不留下后台服务。"""
        self._stop.set()
        if self._connection:
            try:
                self._connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._connection.close()
        if self._socket:
            self._socket.close()
        if self._thread:
            self._thread.join(timeout=3)

    def _sdp(self):
        """从合成编码的SPS/PPS构造独立预期的H264媒体描述。"""
        sps = next(n for n in self._nals if n[0] & 31 == 7)
        pps = next(n for n in self._nals if n[0] & 31 == 8)
        description = ("v=0\r\no=- 1 1 IN IP4 127.0.0.1\r\ns=Synthetic test only\r\n"
                       "c=IN IP4 127.0.0.1\r\nt=0 0\r\na=control:*\r\n"
                       "m=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\n"
                       "a=fmtp:96 packetization-mode=1;profile-level-id=%s;sprop-parameter-sets=%s,%s\r\n"
                       "a=control:trackID=0\r\n") % (
                           sps[1:4].hex(), base64.b64encode(sps).decode(), base64.b64encode(pps).decode())
        return description.encode()

    def _reply(self, connection, cseq, headers="", body=b""):
        """发送最小RTSP控制响应；只回传测试协议内容。"""
        response = ("RTSP/1.0 200 OK\r\nCSeq: %s\r\nSession: synthetic-only\r\n%s"
                    "Content-Length: %d\r\n\r\n") % (cseq, headers, len(body))
        connection.sendall(response.encode() + body)

    def _stream(self, connection):
        """TCP交错RTP含FU-A分片，每帧增长时间戳；不依赖UDP或外部媒体服务。"""
        sequence, timestamp = 0, 0
        while not self._stop.is_set():
            for nal in self._nals:
                end_frame = nal[0] & 31 in (1, 5)
                fragments = [nal]
                if len(nal) > 1200:
                    pieces = [nal[i:i + 1198] for i in range(1, len(nal), 1198)]
                    fragments = [bytes([(nal[0] & 0xE0) | 28,
                                        (nal[0] & 31) | (0x80 if i == 0 else 0)
                                        | (0x40 if i == len(pieces) - 1 else 0)]) + piece
                                 for i, piece in enumerate(pieces)]
                for index, fragment in enumerate(fragments):
                    marker = end_frame and index == len(fragments) - 1
                    packet = struct.pack("!BBHII", 0x80, 96 | (0x80 if marker else 0), sequence,
                                         timestamp, 12345) + fragment
                    connection.sendall(b"$\x00" + struct.pack("!H", len(packet)) + packet)
                    sequence = (sequence + 1) % 65536
                if end_frame:
                    timestamp = (timestamp + 18000) % 2**32
            time.sleep(0.2)

    def _serve(self):
        """处理标准拉流控制步骤，传输异常仅结束fixture客户端。"""
        while not self._stop.is_set():
            try:
                connection, _peer = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self._connection = connection
            with connection:
                connection.settimeout(3)
                pending = b""
                try:
                    while not self._stop.is_set():
                        while b"\r\n\r\n" not in pending:
                            block = connection.recv(8192)
                            if not block:
                                return
                            pending += block
                        request, pending = pending.split(b"\r\n\r\n", 1)
                        lines = request.decode().split("\r\n")
                        method = lines[0].split()[0]
                        headers = dict(line.split(":", 1) for line in lines[1:] if ":" in line)
                        cseq = headers.get("CSeq", "1").strip()
                        if method == "DESCRIBE":
                            self._reply(connection, cseq, "Content-Type: application/sdp\r\n"
                                        "Content-Base: rtsp://127.0.0.1:10554/live/synthetic-video/\r\n", self._sdp())
                        elif method == "SETUP":
                            self._reply(connection, cseq, "Transport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n")
                        elif method == "PLAY":
                            self._reply(connection, cseq, "Range: npt=0-\r\n")
                            self._stream(connection)
                            break
                        else:
                            self._reply(connection, cseq, "Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n")
                except (OSError, UnicodeError):
                    pass
