import mmap
import struct
import time


class MemoryShareManager:
    """内存共享管理器，用于在进程间共享心率数据"""
    
    # 共享内存区域的名称
    SHARED_MEM_NAME = "HeartRateSharedMemory"
    # 共享内存的大小（字节）
    SHARED_MEM_SIZE = 4096
    # 数据结构体格式（seq: 递增序列号, BPM: int, timestamp: float）
    # seq 用于读取方校验是否读到完整的单次写入，避免读到半写数据
    DATA_FORMAT = "Iif"
    # 数据大小
    DATA_SIZE = struct.calcsize(DATA_FORMAT)

    def __init__(self):
        self.shared_memory = None
        self.mmap_obj = None
        self.is_initialized = False
        self._write_seq = 0
    
    def initialize(self):
        """初始化共享内存"""
        try:
            # 创建或打开共享内存区域
            self.shared_memory = mmap.mmap(
                -1,  # 使用匿名映射，或者指定文件描述符
                self.SHARED_MEM_SIZE,
                self.SHARED_MEM_NAME,
                mmap.ACCESS_WRITE
            )
            self.is_initialized = True
            print(f"[MemoryShare] 共享内存已创建: {self.SHARED_MEM_NAME}")
        except Exception as e:
            print(f"[MemoryShare] 初始化共享内存失败: {e}")
            self.is_initialized = False
    
    def update_heart_rate(self, heart_rate):
        """更新共享内存中的心率数据"""
        if not self.is_initialized:
            return
        
        try:
            # 获取当前时间戳
            timestamp = time.time()
            
            # 递增序列号：读取方据此判断数据是否完整（未被写中断）
            self._write_seq += 1
            
            # 打包数据
            data = struct.pack(self.DATA_FORMAT, self._write_seq, heart_rate, timestamp)
            
            # 写入共享内存
            self.shared_memory.seek(0)
            self.shared_memory.write(data)
            self.shared_memory.flush()
            
        except Exception as e:
            print(f"[MemoryShare] 更新心率数据失败: {e}")
    
    def close(self):
        """关闭共享内存"""
        if self.shared_memory:
            try:
                self.shared_memory.close()
                print(f"[MemoryShare] 共享内存已关闭: {self.SHARED_MEM_NAME}")
            except Exception as e:
                print(f"[MemoryShare] 关闭共享内存失败: {e}")
            finally:
                self.shared_memory = None
                self.is_initialized = False
    
    def __del__(self):
        """析构函数，确保共享内存被关闭"""
        self.close()


# 用于外部程序读取共享内存的辅助函数
def read_heart_rate_from_memory():
    """从共享内存中读取心率数据

    通过连续两次读取序列号并比对，避免读到写入中途的半写数据。

    Returns:
        tuple: (heart_rate, timestamp) 或 None
    """
    try:
        with mmap.mmap(
            -1,
            MemoryShareManager.SHARED_MEM_SIZE,
            MemoryShareManager.SHARED_MEM_NAME,
            mmap.ACCESS_READ
        ) as shared_memory:
            # 最多重试 3 次以消除瞬时写竞争
            for _ in range(3):
                shared_memory.seek(0)
                first = shared_memory.read(MemoryShareManager.DATA_SIZE)
                if len(first) != MemoryShareManager.DATA_SIZE:
                    return None
                seq1 = struct.unpack('I', first[0:4])[0]

                shared_memory.seek(0)
                second = shared_memory.read(MemoryShareManager.DATA_SIZE)
                seq2 = struct.unpack('I', second[0:4])[0]

                if seq1 == seq2 and seq1 != 0:
                    _, heart_rate, timestamp = struct.unpack(
                        MemoryShareManager.DATA_FORMAT, second
                    )
                    return heart_rate, timestamp

                time.sleep(0.001)
            return None
    except Exception as e:
        print(f"[MemoryShare] 读取心率数据失败: {e}")
        return None
