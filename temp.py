import subprocess
import glob
import re

def is_main_video_device(dev, timeout=1.0):
    try:
        # 检查 Video Capture
        info = subprocess.run(
            ['v4l2-ctl', '--device', dev, '--all'],
            capture_output=True, text=True, timeout=timeout
        )
        if 'Video Capture' not in info.stdout:
            return False

        # 检查常见的图像格式
        formats = subprocess.run(
            ['v4l2-ctl', '--device', dev, '--list-formats-ext'],
            capture_output=True, text=True, timeout=timeout
        ).stdout

        return bool(re.search(r'YUYV|MJPG|RGB3|NV12', formats))

    except subprocess.TimeoutExpired:
        # 设备响应太慢，跳过
        print(f'{dev} 响应超时，跳过')
        return False
    except subprocess.CalledProcessError:
        # v4l2-ctl 返回非零时也跳过
        print(f'{dev} 调用失败，跳过')
        return False

if __name__ == '__main__':
    video_devices = sorted(glob.glob('/dev/video*'))
    for dev in video_devices:
        print(dev)
        if is_main_video_device(dev):
            print(f'{dev} ✅ 主摄像头接口')
        else:
            print(f'{dev} ❌ 非主接口或跳过')
