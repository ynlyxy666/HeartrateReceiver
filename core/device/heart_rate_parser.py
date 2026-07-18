"""蓝牙心率数据解析器，遵循 Heart Rate Service 规范"""

import logging
from typing import Optional


class HeartRateParser:
    """蓝牙心率数据解析器，遵循 Heart Rate Service 标准协议"""

    # 标志位掩码
    HR_VALUE_FORMAT_MASK = 0x01      # 0 = 8-bit, 1 = 16-bit
    SENSOR_CONTACT_STATUS_MASK = 0x06
    SENSOR_CONTACT_SUPPORTED_MASK = 0x04
    RR_INTERVAL_MASK = 0x10

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parse_errors = 0
        self.success_count = 0
        self.max_logged_errors = 5

    def parse_heart_rate_measurement(self, data: bytearray) -> dict:
        """
        解析心率测量数据

        Args:
            data: 原始字节数组数据

        Returns:
            包含解析结果的字典:
            {
                'heart_rate': int,           # 心率值
                'is_16bit': bool,            # 是否为16位格式
                'sensor_contact': Optional[str],  # 传感器接触状态
                'rr_intervals': list[int]    # RR间隔数组
            }

        Raises:
            ValueError: 当数据格式无效时
        """
        if not data or len(data) < 2:
            raise ValueError(f"数据长度无效: {len(data) if data else 0}")

        try:
            flags = data[0]
            result = {
                'heart_rate': None,
                'is_16bit': bool(flags & self.HR_VALUE_FORMAT_MASK),
                'sensor_contact': None,
                'rr_intervals': []
            }

            # 解析心率值
            offset = 1
            if result['is_16bit']:
                if len(data) < 3:
                    raise ValueError("16位心率数据长度不足")
                result['heart_rate'] = int.from_bytes(data[1:3], byteorder='little')
                offset = 3
            else:
                result['heart_rate'] = data[1]
                offset = 2

            # 解析传感器接触状态
            if flags & self.SENSOR_CONTACT_SUPPORTED_MASK:
                sensor_status = (flags & self.SENSOR_CONTACT_STATUS_MASK) >> 1
                if sensor_status == 0:
                    result['sensor_contact'] = 'not_supported'
                elif sensor_status == 1:
                    result['sensor_contact'] = 'no_contact'
                elif sensor_status == 2:
                    result['sensor_contact'] = 'contact'
                elif sensor_status == 3:
                    result['sensor_contact'] = 'contact_detected'

            # 解析RR间隔（如果存在）
            if flags & self.RR_INTERVAL_MASK:
                while offset + 1 < len(data):
                    rr_interval = int.from_bytes(data[offset:offset+2], byteorder='little')
                    result['rr_intervals'].append(rr_interval)
                    offset += 2

            self.success_count += 1
            return result

        except ValueError:
            self.parse_errors += 1
            raise
        except Exception as e:
            self.parse_errors += 1
            raise ValueError(f"心率数据解析异常: {e}, 原始数据: {data.hex()}") from e

    def get_statistics(self) -> dict:
        """获取解析统计信息"""
        total = self.success_count + self.parse_errors
        success_rate = (self.success_count / total * 100) if total > 0 else 0
        return {
            'success_count': self.success_count,
            'error_count': self.parse_errors,
            'success_rate': f"{success_rate:.1f}%"
        }
