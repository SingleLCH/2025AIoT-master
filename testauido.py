import subprocess
import time

# 测试的设备列表
devices = range(0,30)

# 你要播放的测试音频文件名
wav_file = "wake.wav"

for device in devices:
    device_str = f"hw:{device},0"
    print(f"\nTesting device {device_str}...")
    try:
        # 调用 aplay 播放
        result = subprocess.run(
            ["aplay", "-D", device_str, wav_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5
        )
        print(result.stdout.decode())
    except subprocess.TimeoutExpired:
        print(f"Device {device_str}: aplay timed out.")
    except Exception as e:
        print(f"Device {device_str}: Error occurred: {e}")
    
    time.sleep(2)
