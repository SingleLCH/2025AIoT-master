import subprocess
import sys
import time
import signal
import os

def getSoundCardIndex():
    cardName = "lahainayupikiot"
    try:
        ret = subprocess.run(["cat", "/proc/asound/cards"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = ret.stdout
        lines = output.splitlines()
        for line in lines:
            if cardName in line:
                cindex = line.split()[0]
                return cindex
        print(f"card '{cardName}' not found in /proc/asound/cards.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e.stderr}")
        return None

def setSoundMixerCommand(index):
    commands = [
        # 输入路径设置
        ["amixer", "-c", str(index), "cset", "numid=128,iface=MIXER,name='MultiMedia1 Mixer TX_CDC_DMA_TX_3'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=127,iface=MIXER,name='TX_CDC_DMA_TX_3 Channels'", "Two"],
        ["amixer", "-c", str(index), "cset", "numid=126,iface=MIXER,name='TX DEC0 MUX'", "SWR_MIC"],
        ["amixer", "-c", str(index), "cset", "numid=125,iface=MIXER,name='TX SMIC MUX0'", "ADC1"],
        ["amixer", "-c", str(index), "cset", "numid=124,iface=MIXER,name='TX_AIF1_CAP Mixer DEC0'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=123,iface=MIXER,name='TX_AIF1_CAP Mixer DEC1'", "1"],
        
        # 输出路径设置（保留原有输出设置）
        ["amixer", "-c", str(index), "cset", "numid=243,iface=MIXER,name='RX HPH Mode'", "CLS_AB"],
        ["amixer", "-c", str(index), "cset", "numid=90,iface=MIXER,name='RX_MACRO RX0 MUX'", "AIF1_PB"],
        ["amixer", "-c", str(index), "cset", "numid=91,iface=MIXER,name='RX_MACRO RX1 MUX'", "AIF1_PB"],
        ["amixer", "-c", str(index), "cset", "numid=6639,iface=MIXER,name='RX_CDC_DMA_RX_0 Channels'", "Two"],
        ["amixer", "-c", str(index), "cset", "numid=112,iface=MIXER,name='RX INT0_1 MIX1 INP0'", "RX0"],
        ["amixer", "-c", str(index), "cset", "numid=115,iface=MIXER,name='RX INT1_1 MIX1 INP0'", "RX1"],
        ["amixer", "-c", str(index), "cset", "numid=107,iface=MIXER,name='RX INT0 DEM MUX'", "CLSH_DSM_OUT"],
        ["amixer", "-c", str(index), "cset", "numid=108,iface=MIXER,name='RX INT1 DEM MUX'", "CLSH_DSM_OUT"],
        ["amixer", "-c", str(index), "cset", "numid=137,iface=MIXER,name='RX_COMP1 Switch'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=138,iface=MIXER,name='RX_COMP2 Switch'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=244,iface=MIXER,name='HPHL_COMP Switch'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=245,iface=MIXER,name='HPHR_COMP Switch'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=269,iface=MIXER,name='HPHL_RDAC Switch'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=270,iface=MIXER,name='HPHR_RDAC Switch'", "1"],
        ["amixer", "-c", str(index), "cset", "numid=520,iface=MIXER,name='RX_CDC_DMA_RX_0 Audio Mixer MultiMedia1'", "1"]
    ]

    for cmd in commands:
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"Command {' '.join(cmd)} executed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Command {' '.join(cmd)} failed with error: {e.stderr}")

def startAudioLoopback(card_index):
    """启动麦克风到扬声器的实时串流"""
    # 创建管道连接录音和播放进程
    arecord_cmd = [
        'arecord', '-t', 'raw',
        '-r', '48000',             # 采样率
        '-f', 'S16_LE',            # 音频格式
        '-c', '2',                 # 双声道
        '-D', 'hw:0,0'  # 使用TX_CDC_DMA_TX_3接口
    ]
    
    aplay_cmd = [
        'aplay', '-t', 'raw',
        '-r', '48000',
        '-f', 'S16_LE',
        '-c', '2',
        '-D', f'hw:{card_index},0'  # 播放到设备0
    ]
    
    try:
        print("Starting audio loopback... (Press Ctrl+C to stop)")
        
        # 启动录音进程
        recorder = subprocess.Popen(
            arecord_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 启动播放进程，连接到录音进程的输出
        player = subprocess.Popen(
            aplay_cmd,
            stdin=recorder.stdout,
            stderr=subprocess.PIPE
        )
        
        # 等待进程结束
        recorder.stdout.close()  # 允许recorder收到SIGPIPE
        player.communicate()     # 等待播放进程结束
        
    except KeyboardInterrupt:
        print("\nStopping audio loopback...")
    finally:
        # 确保终止所有进程
        if recorder.poll() is None:
            recorder.terminate()
        if player.poll() is None:
            player.terminate()
        recorder.wait()
        player.wait()

if __name__ == "__main__":
    cardIndex = getSoundCardIndex()
    if cardIndex is None:
        print("Error: Failed to get sound card index. Exiting.")
        sys.exit(1000)
    
    setSoundMixerCommand(cardIndex)
    startAudioLoopback(cardIndex)