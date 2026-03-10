import subprocess
import sys
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioPlayer:
    def __init__(self, card_name="lahainayupikiot"):
        """
        初始化音频播放器
        
        Args:
            card_name (str): 声卡名称，默认为"lahainayupikiot"
        """
        self.card_name = card_name
        self.card_index = None
        self._initialized = False
    
    def get_sound_card_index(self):
        """
        获取指定声卡的索引
        
        Returns:
            str: 声卡索引，如果未找到返回None
        """
        try:
            ret = subprocess.run(["cat", "/proc/asound/cards"], 
                               check=True, stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, text=True)
            output = ret.stdout
            lines = output.splitlines()
            for line in lines:
                if self.card_name in line:
                    cindex = line.split()[0]
                    logger.info(f"找到声卡 '{self.card_name}'，索引: {cindex}")
                    return cindex
            logger.warning(f"未找到声卡 '{self.card_name}' 在 /proc/asound/cards 中")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"获取声卡信息失败: {e.stderr}")
            return None
    
    def set_sound_mixer_commands(self, index):
        """
        设置声卡混音器参数
        
        Args:
            index (str): 声卡索引
            
        Returns:
            bool: 设置成功返回True，失败返回False
        """
        commands = [
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
        
        success = True
        for cmd in commands:
            try:
                result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, text=True)
                logger.debug(f"混音器命令执行成功: {' '.join(cmd)}")
            except subprocess.CalledProcessError as e:
                logger.error(f"混音器命令执行失败: {' '.join(cmd)}")
                logger.error(f"错误信息: {e.stderr}")
                success = False
        
        if success:
            logger.info("声卡混音器设置完成")
        return success
    
    def _play_audio_file(self, card_index, audio_file):
        """
        播放音频文件的底层实现
        
        Args:
            card_index (str): 声卡索引
            audio_file (str): 音频文件路径
            
        Returns:
            bool: 播放成功返回True，失败返回False
        """
        # 根据文件扩展名选择播放命令
        file_ext = os.path.splitext(audio_file)[1].lower()
        
        if file_ext == '.wav':
            # WAV文件使用aplay（这是我们的专用播放代码）
            pcom = ['aplay', '-t', 'wav', '-r', '48000', '-f', 'S16_BE', 
                    '-c', '2', '-D', f'hw:{card_index},0', audio_file]
        elif file_ext == '.mp3':
            # MP3文件使用mpg123或类似工具
            # 针对Linux系统优化的MP3播放器配置
            mp3_players = [
                # 使用mpg123（最常用的MP3播放器）
                ['mpg123', '-a', f'hw:{card_index},0', audio_file],
                ['mpg123', '-o', 'alsa', '-a', f'hw:{card_index},0', audio_file],
                ['mpg123', audio_file],  # 使用默认音频设备
                
                # 使用mplayer
                ['mplayer', '-ao', f'alsa:device=hw={card_index}.0', audio_file],
                ['mplayer', '-quiet', '-ao', f'alsa:device=hw={card_index}.0', audio_file],
                ['mplayer', audio_file],  # 使用默认音频设备
                
                # 使用ffplay
                ['ffplay', '-nodisp', '-autoexit', audio_file],
                ['ffplay', '-nodisp', '-autoexit', '-f', 'mp3', audio_file],
                
                # 使用sox (如果安装了)
                ['sox', audio_file, '-d'],
                
                # 使用aplay通过转换(如果其他都失败)
                ['ffmpeg', '-i', audio_file, '-f', 'wav', '-', '|', 'aplay', '-D', f'hw:{card_index},0'],
            ]
            
            for pcom in mp3_players:
                try:
                    # 🔧 修复：使用Popen启动非阻塞进程，不等待完成
                    # 如果命令包含管道，使用shell=True
                    use_shell = '|' in ' '.join(pcom)
                    
                    if use_shell:
                        cmd_str = ' '.join(pcom)
                        process = subprocess.Popen(cmd_str, shell=True, 
                                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    else:
                        process = subprocess.Popen(pcom, stdout=subprocess.PIPE, 
                                                 stderr=subprocess.PIPE, text=True)
                    
                    # 短暂等待确认进程启动成功
                    import time
                    time.sleep(0.2)
                    
                    # 检查进程是否还在运行
                    if process.poll() is None:
                        # 进程仍在运行，说明启动成功
                        logger.info(f"音频播放成功: {audio_file} (使用 {pcom[0]})")
                        
                        # 将进程保存以便管理
                        _store_audio_process(process)
                        return True
                    else:
                        # 进程已结束，可能是启动失败
                        logger.debug(f"播放器 {pcom[0]} 进程立即结束")
                        continue
                        
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logger.debug(f"播放器 {pcom[0]} 失败: {e}")
                    continue
            
            logger.error(f"所有MP3播放器都无法播放文件: {audio_file}")
            logger.error("请安装以下工具之一: mpg123, mplayer, ffmpeg, sox")
            logger.error("Ubuntu/Debian: sudo apt-get install mpg123")
            logger.error("CentOS/RHEL: sudo yum install mpg123")
            return False
        else:
            logger.error(f"不支持的音频格式: {file_ext}")
            return False
        
        # 执行WAV播放命令（非阻塞方式）
        try:
            # 使用Popen启动非阻塞进程
            process = subprocess.Popen(pcom, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, text=True)
            
            # 不等待进程结束，立即返回
            logger.info(f"音频播放启动: {audio_file} (PID: {process.pid})")
            
            # 将进程ID保存，以便后续可能需要停止
            _store_audio_process(process)
            
            return True
        except Exception as e:
            logger.error(f"音频播放启动失败: {' '.join(pcom)}")
            logger.error(f"错误信息: {e}")
            return False
    
    def initialize(self):
        """
        初始化音频播放器（获取声卡索引并设置混音器）
        
        Returns:
            bool: 初始化成功返回True，失败返回False
        """
        if self._initialized:
            return True
            
        # 获取声卡索引
        self.card_index = self.get_sound_card_index()
        if self.card_index is None:
            logger.error("初始化失败：无法找到声卡")
            return False
        
        # 设置混音器
        if not self.set_sound_mixer_commands(self.card_index):
            logger.error("初始化失败：混音器设置失败")
            return False
        
        self._initialized = True
        logger.info("音频播放器初始化成功")
        return True
    
    def play(self, audio_file):
        """
        播放音频文件（主要接口，非阻塞）
        
        Args:
            audio_file (str): 音频文件路径
            
        Returns:
            bool: 播放成功返回True，失败返回False
        """
        # 检查文件是否存在
        if not os.path.exists(audio_file):
            logger.error(f"音频文件不存在: {audio_file}")
            return False
        
        # 如果未初始化，先进行初始化
        if not self._initialized:
            if not self.initialize():
                return False
        
        # 播放音频
        return self._play_audio_file(self.card_index, audio_file)
    
    def play_wav_blocking(self, audio_file):
        """
        播放WAV音频文件（阻塞版本，用于TTS播放避免死循环）
        
        Args:
            audio_file (str): 音频文件路径
            
        Returns:
            bool: 播放成功返回True，失败返回False
        """
        # 检查文件是否存在
        if not os.path.exists(audio_file):
            logger.error(f"音频文件不存在: {audio_file}")
            return False
        
        # 如果未初始化，先进行初始化
        if not self._initialized:
            if not self.initialize():
                return False
        
        # 阻塞播放WAV文件
        return self._play_wav_blocking(self.card_index, audio_file)
    
    def _play_wav_blocking(self, card_index, audio_file):
        """
        阻塞播放WAV文件（内部方法）- 🔧 增强版本：支持中断检查
        
        Args:
            card_index (str): 声卡索引
            audio_file (str): 音频文件路径
            
        Returns:
            bool: 播放成功返回True，失败返回False
        """
        # 只处理WAV文件
        file_ext = os.path.splitext(audio_file)[1].lower()
        if file_ext != '.wav':
            logger.error(f"阻塞播放只支持WAV格式，当前文件: {file_ext}")
            return False
        
        # 🔧 检查是否是音乐文件，如果是则使用支持中断的播放方式
        is_music_file = "music_" in audio_file and audio_file.endswith('.wav')
        
        if is_music_file:
            # 音乐文件：使用支持中断的非阻塞播放
            logger.info(f"检测到音乐文件，使用支持中断的播放方式: {audio_file}")
            return self._play_wav_with_interrupt_support(card_index, audio_file)
        else:
            # TTS文件：使用传统阻塞播放
            return self._play_wav_traditional_blocking(card_index, audio_file)
    
    def _play_wav_with_interrupt_support(self, card_index, audio_file):
        """
        支持中断的WAV播放（用于音乐）
        
        Args:
            card_index (str): 声卡索引
            audio_file (str): 音频文件路径
            
        Returns:
            bool: 播放成功返回True，失败或被中断返回False
        """
        import time
        import threading
        
        # 🔧 修复：使用完整的格式参数，确保与转换后的WAV文件格式匹配
        play_command = ['aplay', '-D', f'plughw:{card_index},0', audio_file]
        method_number = 4
        
        try:
            # 启动播放进程（非阻塞）
            process = subprocess.Popen(play_command, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, text=True)
            
            # 存储进程用于管理
            global _audio_processes
            _audio_processes.append(process)
            
            logger.info(f"音乐播放进程已启动: PID {process.pid} (方法{method_number})")
            
            # 监控播放进程和中断标志
            check_interval = 0.5  # 每500ms检查一次
            
            while process.poll() is None:  # 进程仍在运行
                # 🔧 检查全局中断标志
                try:
                    import sys
                    if 'xiaoxin2_zh' in sys.modules:
                        xiaoxin2_zh = sys.modules['xiaoxin2_zh']
                        if hasattr(xiaoxin2_zh, 'tts_interrupt_flag') and xiaoxin2_zh.tts_interrupt_flag:
                            logger.info(f"🛑 检测到中断标志，停止音乐播放进程: PID {process.pid}")
                            process.terminate()
                            try:
                                process.wait(timeout=2)  # 等待进程结束
                            except subprocess.TimeoutExpired:
                                process.kill()  # 强制杀死
                                process.wait()
                            logger.info(f"✅ 音乐播放进程已被中断: PID {process.pid}")
                            return False
                except ImportError:
                    # 如果无法导入主模块，忽略中断检查
                    pass
                
                time.sleep(check_interval)
            
            # 检查播放结果
            return_code = process.returncode
            if return_code == 0:
                logger.info(f"音频播放完成: {audio_file} (方法{method_number})")
                return True
            else:
                logger.error(f"播放方法{method_number}失败，返回码: {return_code}")
                return False
                
        except Exception as e:
            logger.error(f"播放方法{method_number}异常: {e}")
            return False
    
    def _play_wav_traditional_blocking(self, card_index, audio_file):
        """
        传统阻塞播放WAV文件（用于TTS）
        
        Args:
            card_index (str): 声卡索引
            audio_file (str): 音频文件路径
            
        Returns:
            bool: 播放成功返回True，失败返回False
        """
        # 🔧 修复：使用完整的格式参数，确保与转换后的WAV文件格式匹配  
        play_command = ['aplay', '-D', f'plughw:{card_index},0', audio_file]
        method_number = 4
        
        try:
            # TTS文件：保持原有的30秒超时
            timeout_value = 30
            
            result = subprocess.run(play_command, check=True, stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, text=True, timeout=timeout_value)
            logger.info(f"TTS音频播放完成: {audio_file} (方法{method_number})")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"播放方法{method_number}失败: {' '.join(play_command)}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"播放方法{method_number}超时（timeout={timeout_value}s）")
            return False
        except Exception as e:
            logger.error(f"播放方法{method_number}异常: {e}")
            return False


# 创建全局音频播放器实例
_global_player = None

# 音频进程管理
_audio_processes = []

def _store_audio_process(process):
    """存储音频播放进程"""
    global _audio_processes
    _audio_processes.append(process)
    
    # 清理已结束的进程
    _audio_processes = [p for p in _audio_processes if p.poll() is None]

def stop_all_audio():
    """停止所有音频播放进程"""
    global _audio_processes
    stopped_count = 0
    
    for process in _audio_processes:
        try:
            if process.poll() is None:  # 进程仍在运行
                process.terminate()
                stopped_count += 1
                logger.info(f"停止音频进程: PID {process.pid}")
        except Exception as e:
            logger.warning(f"停止音频进程失败: {e}")
    
    _audio_processes.clear()
    return stopped_count

def get_audio_player():
    """
    获取全局音频播放器实例（单例模式）
    
    Returns:
        AudioPlayer: 音频播放器实例
    """
    global _global_player
    if _global_player is None:
        _global_player = AudioPlayer()
    return _global_player

def play_audio(audio_file):
    """
    简单的音频播放函数（非阻塞，推荐用于音乐播放）
    
    Args:
        audio_file (str): 音频文件路径
        
    Returns:
        bool: 播放成功返回True，失败返回False
    """
    player = get_audio_player()
    return player.play(audio_file)

def play_audio_blocking(audio_file):
    """
    阻塞版本的音频播放函数（用于TTS播放避免死循环）
    
    Args:
        audio_file (str): 音频文件路径
        
    Returns:
        bool: 播放成功返回True，失败返回False
    """
    player = get_audio_player()
    return player.play_wav_blocking(audio_file)


if __name__ == "__main__":
    # 命令行使用方式（保持与原代码兼容）
    if len(sys.argv) == 2:
        audio_file = sys.argv[1]
        success = play_audio(audio_file)
        if not success:
            sys.exit(1)
    else:
        print("使用方法: python audio_player.py <音频文件路径>")
        print("或者在代码中导入: from audio_player import play_audio") 