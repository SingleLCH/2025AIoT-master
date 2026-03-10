#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ALSA CosyVoice流式语音合成模块

功能：
- 使用阿里云CosyVoice流式API
- 直接输出PCM音频流
- 使用ALSA层的aplay直接播放
- 避免文件保存，提高响应速度
"""

import os
import subprocess
import threading
import time
import queue
from typing import Optional, Callable, Iterator
from dotenv import load_dotenv

# 阿里云语音流式合成相关导入
try:
    import dashscope
    from dashscope.audio.tts_v2 import *
    COSYVOICE_AVAILABLE = True
except ImportError:
    print("⚠️ 阿里云CosyVoice SDK未安装")
    COSYVOICE_AVAILABLE = False

# 加载环境变量
load_dotenv("xiaoxin.env")

class ALSACosyVoiceTTS:
    """ALSA CosyVoice流式语音合成器"""
    
    def __init__(self, card_name="lahainayupikiot"):
        """
        初始化ALSA CosyVoice TTS
        
        Args:
            card_name: 声卡名称
        """
        self.card_name = card_name
        self.card_index = None
        
        # CosyVoice配置
        if COSYVOICE_AVAILABLE:
            self.api_key = os.environ.get("DASHSCOPE_API_KEY")
            dashscope.api_key = self.api_key
        
        # 流式合成参数
        self.model = "cosyvoice-v1"
        # 🔧 从环境变量读取语音配置
        self.voice = os.environ.get("Azure_speech_speaker", "longwan")  # 使用longwan声音
        self.sample_rate = 22050  # CosyVoice实际输出采样率
        self.channels = 1  # CosyVoice实际输出单声道
        self.format = "pcm"  # PCM格式（转换后）
        
        # 播放控制
        self.is_playing = False
        self.play_process = None
        self.play_thread = None
        self.audio_queue = queue.Queue()
        
        print(f"🎵 初始化ALSA CosyVoice TTS")
        print(f"   声卡: {self.card_name}")
        print(f"   模型: {self.model}")
        print(f"   音色: {self.voice}")
        
    def get_sound_card_index(self):
        """获取指定声卡的索引"""
        try:
            ret = subprocess.run(["cat", "/proc/asound/cards"], 
                               check=True, stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, text=True)
            output = ret.stdout
            lines = output.splitlines()
            for line in lines:
                if self.card_name in line:
                    cindex = line.split()[0]
                    print(f"✅ 找到声卡 '{self.card_name}'，索引: {cindex}")
                    return cindex
            print(f"❌ 未找到声卡 '{self.card_name}'")
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ 获取声卡信息失败: {e.stderr}")
            return None
    
    def setup_mixer_commands(self, index):
        """设置声卡混音器命令（音频输出路径）"""
        commands = [
            # 输出路径设置（与原有设置保持一致）
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
        
        print(f"🔧 配置音频输出路径...")
        for cmd in commands:
            try:
                result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, text=True)
                print(f"   ✅ {' '.join(cmd)}")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ {' '.join(cmd)} 失败: {e.stderr}")
    
    def initialize(self):
        """初始化声卡设备"""
        if not COSYVOICE_AVAILABLE:
            print("❌ CosyVoice SDK不可用")
            return False
        
        # 获取声卡索引
        self.card_index = self.get_sound_card_index()
        if self.card_index is None:
            print("❌ 声卡初始化失败")
            return False
        
        # 设置混音器
        self.setup_mixer_commands(self.card_index)
        
        print("✅ ALSA CosyVoice TTS初始化完成")
        return True
    
    def start_aplay_process(self):
        """启动aplay播放进程"""
        if not self.card_index:
            if not self.initialize():
                return False
        
        # 🔧 设置ALSA播放活跃状态
        try:
            import xiaoxin2_zh
            xiaoxin2_zh.audio_playback_active = True
            print("🔄 设置ALSA播放活跃状态为True")
        except:
            pass
        
        # 构建aplay命令（从stdin读取PCM数据）
        aplay_cmd = [
            'aplay',
            '-t', 'raw',
            '-r', str(self.sample_rate),
            '-f', 'S16_LE',  # 16位小端格式
            '-c', str(self.channels),
            '-D', f'hw:{self.card_index},0'
        ]
        
        try:
            print(f"🔊 启动aplay播放进程...")
            self.play_process = subprocess.Popen(
                aplay_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"✅ aplay播放进程已启动")
            return True
        except Exception as e:
            print(f"❌ 启动aplay进程失败: {e}")
            # 🔧 播放失败时重置状态
            try:
                import xiaoxin2_zh
                xiaoxin2_zh.audio_playback_active = False
                print("🔄 ALSA播放失败，重置状态为False")
            except:
                pass
            return False
    
    def stop_aplay_process(self):
        """停止aplay播放进程"""
        if self.play_process:
            print("🛑 停止aplay播放进程...")
            try:
                # 如果stdin还没有关闭，先关闭它
                if self.play_process.stdin and not self.play_process.stdin.closed:
                    self.play_process.stdin.close()
                
                # 检查进程是否已经结束
                if self.play_process.poll() is None:
                    # 进程还在运行，尝试优雅停止
                    self.play_process.terminate()
                    self.play_process.wait(timeout=5)
                
            except subprocess.TimeoutExpired:
                # 超时则强制杀死进程
                self.play_process.kill()
                self.play_process.wait()
            except:
                # 其他异常也尝试杀死进程
                try:
                    self.play_process.kill()
                    self.play_process.wait()
                except:
                    pass
            
            self.play_process = None
            print("✅ aplay播放进程已停止")
        
        # 🔧 重置ALSA播放活跃状态
        try:
            import xiaoxin2_zh
            xiaoxin2_zh.audio_playback_active = False
            print("🔄 重置ALSA播放活跃状态为False")
        except:
            pass
    
    def synthesize_audio_data_only(self, text: str) -> bytes:
        """
        仅合成音频数据，不播放（用于流式播放）
        
        Args:
            text: 要合成的文本
            
        Returns:
            bytes: 合成的音频数据，失败返回None
        """
        if not text or not text.strip():
            return None
        
        try:
            print(f"🎵 开始音频合成（仅数据）: {text[:30]}...")
            
            # 🔧 合成前检查中断标志
            try:
                import xiaoxin2_zh
                if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                    print("🛑 检测到TTS中断标志，跳过合成")
                    return None
            except:
                pass
            
            # 🔧 使用CosyVoice进行合成
            synthesizer = SpeechSynthesizer(
                model=self.model,
                voice=self.voice
            )
            
            import time
            start_time = time.time()
            
            # 调用合成服务
            audio_data = synthesizer.call(text)
            
            synthesis_time = time.time() - start_time
            
            if audio_data:
                print(f"✅ 音频合成完成（仅数据）(耗时: {synthesis_time:.2f}秒, 数据大小: {len(audio_data)} bytes)")
                return audio_data
            else:
                print("❌ 音频合成失败：无音频数据")
                return None
                
        except Exception as e:
            print(f"❌ 音频合成异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def synthesize_and_play_text(self, text: str) -> bool:
        """
        合成并播放文本（同步版本，支持中断检查） - 🔧 优化版本
        
        Args:
            text: 要合成的文本
            
        Returns:
            bool: 是否成功
        """
        if not text or not text.strip():
            return False
        
        try:
            print(f"🎵 开始语音合成: {text[:30]}...")
            
            # 🔧 合成前检查中断标志
            try:
                import xiaoxin2_zh
                if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                    print("🛑 检测到TTS中断标志，跳过合成")
                    return False
            except:
                pass
            
            # 🔧 优化：使用更快的合成参数
            synthesizer = SpeechSynthesizer(
                model=self.model,
                voice=self.voice
            )
            
            # 🔧 优化：设置更快的网络超时和重试
            import time
            start_time = time.time()
            
            # 使用较短的文本块来减少延迟
            max_chunk_length = 100  # 限制单次合成文本长度
            
            if len(text) <= max_chunk_length:
                # 短文本直接合成
                audio_data = synthesizer.call(text)
                
                if audio_data:
                    synthesis_time = time.time() - start_time
                    print(f"✅ 语音合成完成 (耗时: {synthesis_time:.2f}秒, 数据大小: {len(audio_data)} bytes)")
                    
                    # 🔧 优化：边合成边播放，减少总延迟
                    success = self._play_audio_optimized(audio_data)
                    return success
                else:
                    print("❌ 语音合成失败：无音频数据")
                    return False
            else:
                # 长文本分块合成和播放（流式处理）
                return self._synthesize_long_text_streaming(text, synthesizer)
            
        except Exception as e:
            print(f"❌ 语音合成异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _synthesize_long_text_streaming(self, text: str, synthesizer) -> bool:
        """
        长文本流式合成（分块处理，边合成边播放）
        """
        try:
            # 🔧 智能分段：按句号、感叹号、问号分割
            import re
            sentences = re.split(r'[。！？]', text)
            sentences = [s.strip() + '。' for s in sentences if s.strip()]
            
            if not sentences:
                return False
            
            print(f"🎵 长文本分块合成，共{len(sentences)}段")
            
            # 启动aplay播放进程
            if not self.start_aplay_process():
                return False
            
            try:
                for i, sentence in enumerate(sentences):
                    # 检查中断
                    try:
                        import xiaoxin2_zh
                        if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                            print(f"🛑 第{i+1}段合成时检测到中断")
                            return False
                    except:
                        pass
                    
                    print(f"🔊 合成第{i+1}/{len(sentences)}段: {sentence[:20]}...")
                    
                    # 🔧 优化：并行合成下一段
                    start_time = time.time()
                    audio_data = synthesizer.call(sentence)
                    synthesis_time = time.time() - start_time
                    
                    if audio_data:
                        print(f"✅ 第{i+1}段合成完成 (耗时: {synthesis_time:.2f}秒)")
                        
                        # 检测音频格式并播放
                        if self._is_mp3_data(audio_data):
                            print(f"🎵 检测到MP3格式，转换为PCM...")
                            pcm_data = self._convert_mp3_to_pcm(audio_data)
                            if pcm_data:
                                self._write_pcm_to_aplay(pcm_data)
                        else:
                            # 假设是PCM数据
                            self._write_pcm_to_aplay(audio_data)
                    else:
                        print(f"❌ 第{i+1}段合成失败")
                        
                    # 🔧 优化：短暂延迟，避免过快请求
                    time.sleep(0.1)
                
                print(f"✅ 所有段落合成播放完成")
                return True
                
            finally:
                self.stop_aplay_process()
                
        except Exception as e:
            print(f"❌ 长文本流式合成异常: {e}")
            self.stop_aplay_process()
            return False
    
    def _play_audio_optimized(self, audio_data: bytes) -> bool:
        """
        优化的音频播放函数
        """
        try:
            # 检测音频格式
            if self._is_mp3_data(audio_data):
                print(f"🎵 检测到MP3格式，转换为PCM...")
                pcm_data = self._convert_mp3_to_pcm(audio_data)
                if not pcm_data:
                    return False
            else:
                pcm_data = audio_data
            
            # 启动aplay播放
            if not self.start_aplay_process():
                return False
            
            try:
                # 写入PCM数据
                self._write_pcm_to_aplay(pcm_data)
                
                # 关闭stdin让aplay知道数据已经写完
                if self.play_process and self.play_process.stdin:
                    self.play_process.stdin.close()
                    print(f"🔊 已关闭stdin，等待音频播放完成...")
                
                # 等待aplay进程完成播放
                if self.play_process:
                    try:
                        self.play_process.wait(timeout=10)  # 最多等待10秒
                        print(f"✅ 音频播放完成")
                        return True
                    except subprocess.TimeoutExpired:
                        print(f"⚠️ 音频播放超时，强制停止")
                        self.play_process.kill()
                        return False
                        
            finally:
                self.stop_aplay_process()
                
        except Exception as e:
            print(f"❌ 播放音频失败: {e}")
            return False
    
    def _write_pcm_to_aplay(self, pcm_data: bytes):
        """写入PCM数据到aplay进程"""
        if self.play_process and self.play_process.stdin:
            print(f"🔊 开始播放音频数据...")
            try:
                self.play_process.stdin.write(pcm_data)
                self.play_process.stdin.flush()
                print(f"✅ 音频数据写入完成")
            except BrokenPipeError:
                print(f"❌ 播放音频数据失败: Broken pipe")
                raise
            except Exception as e:
                print(f"❌ 播放音频数据失败: {e}")
                raise
    
    def play_pcm_data(self, audio_data: bytes) -> bool:
        """
        播放音频数据（自动检测格式并转换）
        
        Args:
            audio_data: 音频数据（MP3或PCM）
            
        Returns:
            bool: 是否成功
        """
        try:
            # 检测音频格式
            if self._is_mp3_data(audio_data):
                print(f"🎵 检测到MP3格式，转换为PCM...")
                pcm_data = self._convert_mp3_to_pcm(audio_data)
                if not pcm_data:
                    print(f"❌ MP3转PCM失败")
                    return False
            else:
                print(f"🔊 检测到PCM格式，直接播放...")
                pcm_data = audio_data
            
            # 启动aplay进程
            if not self.start_aplay_process():
                return False
            
            # 写入PCM数据
            print(f"🔊 开始播放音频数据...")
            self.play_process.stdin.write(pcm_data)
            self.play_process.stdin.flush()
            
            # 关闭输入并等待播放完成
            self.play_process.stdin.close()
            self.play_process.wait()
            
            print(f"✅ 音频播放完成")
            self.play_process = None
            
            return True
            
        except Exception as e:
            print(f"❌ 播放音频数据失败: {e}")
            self.stop_aplay_process()
            return False
    
    def play_pcm_data_streaming(self, audio_data: bytes) -> bool:
        """
        流式播放音频数据（保持aplay进程，减少间隔）
        
        Args:
            audio_data: 音频数据（MP3或PCM）
            
        Returns:
            bool: 是否成功
        """
        try:
            # 检查全局中断标志
            try:
                import xiaoxin2_zh
                if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                    print("🛑 检测到TTS中断标志，停止流式播放")
                    self.stop_aplay_process()
                    return False
            except:
                pass  # 忽略导入错误
            
            # 检测音频格式
            if self._is_mp3_data(audio_data):
                pcm_data = self._convert_mp3_to_pcm(audio_data)
                if not pcm_data:
                    print(f"❌ MP3转PCM失败")
                    return False
            else:
                pcm_data = audio_data
            
            # 如果没有运行的aplay进程，启动一个
            if not self.play_process or self.play_process.poll() is not None:
                if not self.start_aplay_process():
                    return False
            
            # 检查进程是否还活着
            if self.play_process.poll() is not None:
                print("⚠️ aplay进程已终止，重新启动")
                if not self.start_aplay_process():
                    return False
            
            # 写入PCM数据（不关闭stdin，保持流式）
            print(f"🔊 流式写入音频片段...")
            try:
                self.play_process.stdin.write(pcm_data)
                self.play_process.stdin.flush()
                print(f"✅ 音频片段已发送")
                return True
            except BrokenPipeError:
                print("❌ 检测到Broken pipe，重新启动aplay进程")
                self.stop_aplay_process()
                # 重试一次
                if self.start_aplay_process():
                    try:
                        self.play_process.stdin.write(pcm_data)
                        self.play_process.stdin.flush()
                        print(f"✅ 重试成功，音频片段已发送")
                        return True
                    except:
                        print("❌ 重试失败")
                        self.stop_aplay_process()
                        return False
                else:
                    return False
            
        except Exception as e:
            print(f"❌ 流式播放音频数据失败: {e}")
            self.stop_aplay_process()
            return False
    
    def finish_streaming_playback(self):
        """完成流式播放（关闭aplay进程）"""
        if self.play_process:
            try:
                print("🏁 完成流式播放，关闭aplay进程...")
                # 确保stdin存在且未关闭
                if self.play_process.stdin and not self.play_process.stdin.closed:
                    self.play_process.stdin.close()
                
                # 等待进程正常结束
                try:
                    self.play_process.wait(timeout=3)
                    print("✅ aplay进程已正常关闭")
                except subprocess.TimeoutExpired:
                    print("⚠️ aplay进程超时，强制终止")
                    self.play_process.kill()
                    self.play_process.wait()
            except:
                print("⚠️ aplay进程强制终止")
                try:
                    self.play_process.kill()
                    self.play_process.wait()
                except:
                    pass
            finally:
                self.play_process = None
        
        # 🔧 重置ALSA播放活跃状态
        try:
            import xiaoxin2_zh
            xiaoxin2_zh.audio_playback_active = False
            print("🔄 流式播放结束，重置ALSA播放活跃状态为False")
        except:
            pass
    
    def _is_mp3_data(self, data: bytes) -> bool:
        """检测是否为MP3数据"""
        # MP3文件通常以ID3标签或音频帧开始
        # ID3v2: 以"ID3"开始
        # 音频帧: 以0xFF 0xFB, 0xFF 0xFA等开始
        if len(data) < 3:
            return False
        
        # 检查ID3标签
        if data[:3] == b'ID3':
            return True
        
        # 检查MP3音频帧同步字节
        if len(data) >= 2:
            first_two = data[:2]
            # MP3帧同步: 前11位都是1 (0xFFE0及以上)
            if first_two[0] == 0xFF and (first_two[1] & 0xE0) == 0xE0:
                return True
        
        return False
    
    def _convert_mp3_to_pcm(self, mp3_data: bytes) -> bytes:
        """将MP3数据转换为PCM数据"""
        import tempfile
        import subprocess
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_file:
                mp3_file.write(mp3_data)
                mp3_path = mp3_file.name
            
            # 使用ffmpeg转换为PCM
            # 输出格式：22050Hz, 单声道, 16位小端
            ffmpeg_cmd = [
                'ffmpeg', '-i', mp3_path,
                '-f', 's16le',         # 16位小端PCM
                '-ac', '1',            # 单声道
                '-ar', '22050',        # 22050Hz采样率
                '-'                    # 输出到stdout
            ]
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                timeout=10
            )
            
            # 清理临时文件
            os.unlink(mp3_path)
            
            if result.returncode == 0:
                print(f"✅ MP3转PCM成功 (PCM大小: {len(result.stdout)} bytes)")
                return result.stdout
            else:
                print(f"❌ ffmpeg转换失败: {result.stderr.decode()}")
                return b''
                
        except Exception as e:
            print(f"❌ MP3转PCM异常: {e}")
            # 清理临时文件
            if 'mp3_path' in locals() and os.path.exists(mp3_path):
                os.unlink(mp3_path)
            return b''
    
    def synthesize_streaming_text(self, text_iterator: Iterator[str], 
                                 callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        流式文本合成（优化版本 - 减少API调用失败）
        
        Args:
            text_iterator: 文本迭代器
            callback: 状态回调函数
            
        Returns:
            bool: 是否成功启动
        """
        
        def streaming_worker():
            try:
                # 启动aplay播放进程
                if not self.start_aplay_process():
                    if callback:
                        callback("播放进程启动失败")
                    return
                
                if callback:
                    callback("开始流式TTS合成...")
                
                success_count = 0
                total_count = 0
                
                for text_chunk in text_iterator:
                    if not text_chunk or not text_chunk.strip():
                        continue
                    
                    total_count += 1
                    
                    # 🔧 每次合成前都检查中断标志
                    try:
                        import xiaoxin2_zh
                        if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                            print(f"🛑 流式TTS在第{total_count}段时被中断")
                            if callback:
                                callback(f"TTS在第{total_count}段时被中断")
                            return
                    except:
                        pass
                    
                    if callback:
                        callback(f"正在合成第{total_count}段: {text_chunk[:20]}...")
                    
                    # 🔧 重试机制：每段最多重试3次
                    max_retries = 3
                    retry_delay = [0.5, 1.0, 2.0]  # 递增延迟
                    
                    for retry in range(max_retries):
                        # 🔧 每次重试前也检查中断标志
                        try:
                            import xiaoxin2_zh
                            if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                                print(f"🛑 流式TTS在第{total_count}段重试{retry+1}时被中断")
                                if callback:
                                    callback(f"TTS在第{total_count}段重试时被中断")
                                return
                        except:
                            pass
                        
                        try:
                            # 合成单个文本块
                            synthesizer = SpeechSynthesizer(
                                model=self.model,
                                voice=self.voice
                            )
                            
                            print(f"🔊 尝试合成第{total_count}段 (重试{retry+1}/{max_retries}): {text_chunk[:20]}...")
                            audio_data = synthesizer.call(text_chunk)
                            
                            if audio_data and len(audio_data) > 1000:  # 检查数据有效性
                                print(f"✅ 第{total_count}段合成成功")
                                success_count += 1
                                
                                # 🔧 播放前再次检查中断标志
                                try:
                                    import xiaoxin2_zh
                                    if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                                        print(f"🛑 流式TTS在第{total_count}段播放前被中断")
                                        if callback:
                                            callback(f"TTS在第{total_count}段播放前被中断")
                                        return
                                except:
                                    pass
                                
                                # 处理音频数据
                                if self._is_mp3_data(audio_data):
                                    print(f"🎵 转换MP3为PCM...")
                                    pcm_data = self._convert_mp3_to_pcm(audio_data)
                                    if pcm_data:
                                        self._write_pcm_to_aplay(pcm_data)
                                else:
                                    # 假设是PCM数据
                                    self._write_pcm_to_aplay(audio_data)
                                
                                # 合成成功，跳出重试循环
                                break
                            else:
                                print(f"⚠️ 第{total_count}段合成数据无效，尝试重试...")
                                if retry < max_retries - 1:
                                    time.sleep(retry_delay[retry])
                                    continue
                        
                        except Exception as e:
                            print(f"❌ 第{total_count}段合成失败 (重试{retry+1}/{max_retries}): {e}")
                            if retry < max_retries - 1:
                                print(f"⏳ 等待{retry_delay[retry]}秒后重试...")
                                time.sleep(retry_delay[retry])
                            else:
                                # 最后一次重试失败
                                print(f"❌ 第{total_count}段最终合成失败，跳过")
                                if callback:
                                    callback(f"第{total_count}段合成失败，跳过")
                    
                    # 🔧 段间延迟前检查中断
                    try:
                        import xiaoxin2_zh
                        if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                            print(f"🛑 流式TTS在段间延迟时被中断")
                            if callback:
                                callback(f"TTS在段间延迟时被中断")
                            return
                    except:
                        pass
                    
                    # 🔧 段间延迟，避免过快请求
                    time.sleep(0.2)
                
                # 完成播放
                if self.play_process:
                    self.play_process.stdin.close()
                    self.play_process.wait()
                    self.play_process = None
                
                if callback:
                    callback(f"流式合成完成：成功{success_count}/{total_count}段")
                    
                print(f"✅ 流式TTS完成：成功合成{success_count}/{total_count}段")
                    
            except Exception as e:
                print(f"❌ 流式合成异常: {e}")
                if callback:
                    callback(f"流式合成错误: {e}")
                # 确保清理播放进程
                self.stop_aplay_process()
        
        # 启动流式工作线程
        self.play_thread = threading.Thread(target=streaming_worker, daemon=True)
        self.play_thread.start()
        
        return True
    
    def interrupt_playback(self):
        """中断当前播放（优雅版本）- 🔧 安全修复"""
        print("🛑 中断音频播放...")
        
        # 🔧 立即设置中断标志
        self.is_playing = False
        
        # 🔧 重置ALSA播放活跃状态
        try:
            import xiaoxin2_zh
            xiaoxin2_zh.audio_playback_active = False
            print("🔄 中断播放，重置ALSA播放活跃状态为False")
        except:
            pass
        
        # 🔧 优雅关闭aplay进程（不强制杀死）
        if self.play_process:
            try:
                print("🔄 优雅停止aplay进程...")
                
                # 首先尝试优雅关闭stdin
                if self.play_process.stdin and not self.play_process.stdin.closed:
                    try:
                        self.play_process.stdin.close()
                        print("✅ stdin已关闭")
                    except:
                        pass
                
                # 等待进程自然结束
                try:
                    self.play_process.wait(timeout=2.0)
                    print("✅ aplay进程已优雅结束")
                except subprocess.TimeoutExpired:
                    print("⚠️ aplay进程等待超时，执行terminate")
                    # 仅在超时时才使用terminate（不用kill）
                    self.play_process.terminate()
                    try:
                        self.play_process.wait(timeout=1.0)
                        print("✅ aplay进程已terminate结束")
                    except subprocess.TimeoutExpired:
                        print("⚠️ terminate超时，进程可能仍在运行")
                
            except Exception as e:
                print(f"❌ 停止aplay进程时出错: {e}")
            finally:
                self.play_process = None
                
        print("✅ 音频播放中断完成")
        
        # 等待线程结束
        if self.play_thread and self.play_thread.is_alive():
            try:
                self.play_thread.join(timeout=1)
                print("✅ 播放线程已结束")
            except:
                print("⚠️ 播放线程结束超时")
            finally:
                self.play_thread = None

# 全局实例
_alsa_tts = None

def get_alsa_tts():
    """获取ALSA CosyVoice TTS单例"""
    global _alsa_tts
    if _alsa_tts is None:
        _alsa_tts = ALSACosyVoiceTTS()
    return _alsa_tts

def text_to_speech_alsa(text: str) -> bool:
    """使用ALSA CosyVoice进行语音合成"""
    tts = get_alsa_tts()
    return tts.synthesize_and_play_text(text)

def text_to_speech_streaming_alsa(text_chunks: Iterator[str], 
                                 callback: Optional[Callable[[str], None]] = None) -> bool:
    """使用ALSA CosyVoice进行流式语音合成"""
    tts = get_alsa_tts()
    return tts.synthesize_streaming_text(text_chunks, callback)

if __name__ == "__main__":
    # 测试ALSA CosyVoice TTS
    tts = ALSACosyVoiceTTS()
    
    if tts.initialize():
        # 测试单句合成
        test_text = "你好，这是ALSA CosyVoice语音合成测试。"
        print(f"测试文本: {test_text}")
        
        success = tts.synthesize_and_play_text(test_text)
        if success:
            print("✅ 测试成功")
        else:
            print("❌ 测试失败")
    else:
        print("❌ 初始化失败") 