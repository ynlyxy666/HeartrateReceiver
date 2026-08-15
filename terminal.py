"""终端日志查看器：流式读取 HypeBeatLogMemory 共享内存中的日志

用法: python terminal.py
Ctrl+C 退出。
"""

import mmap
import struct
import time

NAME = "HypeBeatLogMemory"
SIZE = 1 << 20
HDR = 4  # 头部 4 字节存写偏移


def _open():
    return mmap.mmap(-1, SIZE, NAME, mmap.ACCESS_READ)


def read_since(pos: int):
    """从 pos 读到当前写偏移，返回 (新文本, 新位置)"""
    with _open() as mem:
        offset = struct.unpack('I', mem[0:HDR])[0]
        if offset == pos:
            return "", pos
        if pos < offset:
            data = mem[pos:offset]
            new_pos = offset
        else:  # 写端已回绕，分两段读
            data = mem[pos:SIZE] + mem[HDR:offset]
            new_pos = offset
    return data.decode('utf-8', errors='replace'), new_pos


if __name__ == "__main__":
    pos = HDR
    while True:
        try:
            text, pos = read_since(pos)
            if text:
                print(text, end="")
            time.sleep(0.1)
        except KeyboardInterrupt:
            break
