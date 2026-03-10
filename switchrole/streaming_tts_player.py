#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
流式语音合成和播放模块

功能：
- 支持AI流式生成文本
- 实时语音合成（阿里云CosyVoice流式调用）
- 边生成边合成边播放
- 显著减少总响应时间
"""

import os
import time
import threading
import queue
import re
import logging
import subprocess
from typing import Iterator, Optional, Callable, Tuple
import dashscope
from dashscope.audio.tts_v2 import *
from openai import OpenAI
import tempfile
import platform

# 导入现有的音频播放功能
from audio_priority_manager import AudioPriority, request_audio_access, release_audio_access

# 全局变量
global_streaming_player = None
IS_WINDOWS = platform.system().lower() == "windows"
IS_LINUX = platform.system().lower() == "linux"

def get_global_streaming_player():
    """获取全局流式TTS播放器实例"""
    global global_streaming_player
    if global_streaming_player is None:
        global_streaming_player = StreamingTTSPlayer()
    return global_streaming_player

class StreamingTTSPlayer:
    """流式语音合成播放器"""
    
    def __init__(self, api_key: str, model: str = "cosyvoice-v1", voice: str = "longwan"):
        self.api_key = api_key
        self.model = model
        self.voice = voice
        
        # 设置API Key
        dashscope.api_key = api_key
        
        # 流式控制
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.synthesis_thread = None
        self.is_playing = False
        self.interrupt_flag = False
        
        # 文本处理
        self.sentence_buffer = ""
        self.sentence_patterns = [
            r'[。！？.!?]',  # 句号、感叹号、问号
            r'[，,；;：:]',    # 逗号、分号、冒号（较短停顿）
        ]
        
        print(f"🎵 流式TTS播放器初始化完成 (模型: {model}, 声音: {voice})")
    
    def split_text_by_sentences(self, text: str) -> list:
        """将文本按句子分割"""
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            
            # 检查是否为句子结束标记
            if re.search(r'[。！？.!?]', char):
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
            # 检查是否为较短停顿标记（分割但作为较短片段）
            elif re.search(r'[，,；;：:]', char) and len(current_sentence.strip()) > 10:
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
        
        # 添加剩余文本
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def synthesize_audio_chunk(self, text: str) -> bytes:
        """合成单个文本片段为音频数据"""
        # 🔧 关键修复：在网络请求前检查中断标志
        if self.interrupt_flag:
            print("🛑 合成前检测到中断标志，取消合成")
            return None
        
        # 🔧 关键修复：检查全局中断标志
        try:
            import xiaoxin2_zh
            if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                print("🛑 合成前检测到全局中断标志，取消合成")
                return None
        except:
            pass
        
        try:
            from alsa_cosyvoice_tts import get_alsa_tts
            alsa_tts = get_alsa_tts()
            
            if not alsa_tts:
                print("❌ ALSA TTS实例未初始化")
                return None
            
            # 🔧 关键修复：在调用CosyVoice前再次检查中断
            if self.interrupt_flag:
                print("🛑 调用CosyVoice前检测到中断标志，取消合成")
                return None
            
            # 调用合成服务 - 🔧 修复：使用仅合成音频数据的方法
            audio_data = alsa_tts.synthesize_audio_data_only(text)
            
            # 🔧 关键修复：合成完成后立即检查中断
            if self.interrupt_flag:
                print("🛑 合成完成后检测到中断标志，丢弃音频")
                return None
            
            return audio_data
            
        except Exception as e:
            print(f"❌ 合成音频片段失败: {e}")
            return None
    
    def synthesis_worker(self, text_iterator: Iterator[str]):
        """音频合成工作线程"""
        print("🎤 启动音频合成工作线程")
        
        try:
            for text_chunk in text_iterator:
                # 🔧 关键修复：在处理每个文本片段前立即检查中断标志
                if self.interrupt_flag:
                    print("🛑 语音合成被中断")
                    break
                
                # 🔧 关键修复：强力检查全局中断标志
                try:
                    import xiaoxin2_zh
                    if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                        print("🛑 检测到全局TTS中断标志，立即停止合成")
                        self.interrupt_flag = True
                        # 立即清空队列，防止已合成的音频继续播放
                        try:
                            while not self.audio_queue.empty():
                                self.audio_queue.get_nowait()
                        except:
                            pass
                        # 发送中断信号
                        self.audio_queue.put(('interrupt', None))
                        break
                except:
                    pass  # 忽略导入错误
                
                if text_chunk.strip():
                    print(f"🎤 开始合成: {text_chunk[:30]}...")
                    
                    # 🔧 关键修复：在合成过程中也要检查中断标志
                    if self.interrupt_flag:
                        print("🛑 合成过程中检测到中断标志，立即停止")
                        break
                    
                    start_time = time.time()
                    
                    # 🔧 关键修复：合成前最后一次检查中断标志
                    try:
                        import xiaoxin2_zh
                        if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                            print("🛑 合成前检测到全局中断标志，取消合成")
                            self.interrupt_flag = True
                            break
                    except:
                        pass
                    
                    audio_data = self.synthesize_audio_chunk(text_chunk)
                    
                    # 🔧 关键修复：合成完成后立即检查中断标志
                    if self.interrupt_flag:
                        print("🛑 合成完成后检测到中断标志，丢弃音频数据")
                        break
                    
                    synthesis_time = time.time() - start_time
                    print(f"⚡ 合成完成 (耗时: {synthesis_time:.2f}s): {text_chunk[:20]}...")
                    
                    if audio_data:
                        # 🔧 关键修复：放入队列前再次检查中断标志
                        if self.interrupt_flag:
                            print("🛑 队列前检测到中断标志，丢弃音频数据")
                            break
                        # 将音频数据放入队列
                        self.audio_queue.put(('audio', audio_data))
                    
                    # 🔧 关键修复：避免过快处理时也要检查中断
                    if not self.interrupt_flag:
                        time.sleep(0.1)
            
            # 发送结束信号
            if not self.interrupt_flag:
                self.audio_queue.put(('end', None))
                print("✅ 语音合成工作线程完成")
            else:
                self.audio_queue.put(('interrupt', None))
                print("🛑 语音合成工作线程被中断")
            
        except Exception as e:
            print(f"❌ 语音合成工作线程异常: {e}")
            self.audio_queue.put(('error', str(e)))
        
        print("🏁 音频合成工作线程结束")
    
    def playback_worker(self):
        """音频播放工作线程"""
        print("🔊 启动音频播放工作线程")
        
        audio_files = []  # 临时文件列表，用于清理
        alsa_tts_instance = None  # ALSA TTS实例
        
        try:
            # 初始化ALSA TTS实例（Linux系统）
            if IS_LINUX:
                try:
                    from alsa_cosyvoice_tts import get_alsa_tts
                    alsa_tts_instance = get_alsa_tts()
                    print("🎵 ALSA TTS实例已准备就绪")
                except Exception as e:
                    print(f"⚠️ ALSA TTS初始化失败: {e}")
            
            while True:
                # 检查中断标志
                if self.interrupt_flag:
                    print("🛑 音频播放被中断")
                    break
                
                # 检查全局中断标志
                try:
                    import xiaoxin2_zh
                    if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                        print("🛑 检测到全局TTS中断标志，停止播放")
                        self.interrupt_flag = True
                        break
                except:
                    pass  # 忽略导入错误
                
                try:
                    # 获取音频数据（超时3秒，减少等待时间）
                    item_type, data = self.audio_queue.get(timeout=3)
                    
                    if item_type == 'audio' and data:
                        # 播放音频数据
                        success = self.play_audio_data(data)
                        if success:
                            print("🔊 音频片段播放完成")
                        
                    elif item_type == 'end':
                        print("✅ 所有音频片段播放完成")
                        # 完成流式播放，关闭aplay进程
                        if alsa_tts_instance and IS_LINUX:
                            alsa_tts_instance.finish_streaming_playback()
                        break
                        
                    elif item_type == 'interrupt':
                        print("🛑 接收到中断信号")
                        break
                        
                    elif item_type == 'error':
                        print(f"❌ 播放错误: {data}")
                        break
                        
                except queue.Empty:
                    # 超时，检查是否需要继续等待
                    print("⏰ 音频队列等待超时，检查中断状态")
                    continue
        
        except Exception as e:
            print(f"❌ 音频播放工作线程异常: {e}")
        
        finally:
            # 完成流式播放，关闭aplay进程
            if alsa_tts_instance and IS_LINUX:
                try:
                    alsa_tts_instance.finish_streaming_playback()
                except Exception as e:
                    print(f"⚠️ 关闭ALSA播放进程时出错: {e}")
            
            # 清理临时文件
            self.cleanup_temp_files(audio_files)
            self.is_playing = False
            print("🏁 音频播放工作线程结束")
    
    def play_audio_data(self, audio_data: bytes) -> bool:
        """播放音频数据（使用ALSA连续流播放）"""
        try:
            if IS_LINUX:
                # Linux系统：使用ALSA流式播放
                return self.play_audio_alsa_streaming(audio_data)
            else:
                # 其他系统：使用文件播放方式
                return self.play_audio_file_based(audio_data)
            
        except Exception as e:
            print(f"❌ 播放音频数据失败: {e}")
            return False
    
    def play_audio_alsa_streaming(self, audio_data: bytes) -> bool:
        """使用ALSA连续流播放（避免片段间隔）"""
        try:
            # 使用我们修复过的ALSA CosyVoice模块
            from alsa_cosyvoice_tts import get_alsa_tts
            
            alsa_tts = get_alsa_tts()
            
            # 使用流式播放方法（保持aplay进程运行）
            success = alsa_tts.play_pcm_data_streaming(audio_data)
            
            if success:
                print("🔊 ALSA流式片段已发送")
            else:
                print("❌ ALSA流式片段发送失败")
                
            return success
            
        except Exception as e:
            print(f"❌ ALSA流式播放异常: {e}")
            # 降级到文件播放方式
            return self.play_audio_file_based(audio_data)
    
    def play_audio_file_based(self, audio_data: bytes) -> bool:
        """基于文件的播放方式（备用）"""
        try:
            # 创建临时MP3文件
            temp_file = f"streaming_tts_{int(time.time() * 1000)}.mp3"
            
            with open(temp_file, 'wb') as f:
                f.write(audio_data)
            
            # 使用原有播放方式
            from xiaoxin2_zh import play_mp3_audio
            success = play_mp3_audio(temp_file, "tts")
            
            # 延迟清理文件
            threading.Timer(2.0, self.safe_remove_file, args=(temp_file,)).start()
            
            return success
            
        except Exception as e:
            print(f"❌ 文件播放方式失败: {e}")
            return False
    
    def play_audio_linux_specific(self, audio_file: str) -> bool:
        """
        Linux特定的音频播放方式（适配lahainayupikiot声卡）
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            bool: 播放是否成功
        """
        try:
            # 先将MP3转换为WAV（因为您的播放方式需要WAV格式）
            wav_file = audio_file.replace('.mp3', '.wav')
            
            # 使用ffmpeg转换MP3到WAV，格式匹配您的需求
            convert_cmd = [
                'ffmpeg', '-i', audio_file, 
                '-ar', '48000',           # 采样率48000
                '-ac', '2',               # 双声道
                '-sample_fmt', 's16',     # 16位有符号整数
                '-f', 'wav',              # WAV格式
                '-y',                     # 覆盖输出
                wav_file
            ]
            
            result = subprocess.run(convert_cmd, check=True, 
                                  capture_output=True, text=True)
            print(f"✅ MP3转WAV成功: {wav_file}")
            
            # 使用专用的音频播放器
            from audio_player import get_audio_player
            player = get_audio_player()
            
            # 初始化音频播放器（这会自动设置lahainayupikiot声卡）
            if not player.initialize():
                print("❌ 音频播放器初始化失败")
                return False
            
            # 播放WAV文件（阻塞方式，确保流式播放的连续性）
            success = player.play_wav_blocking(wav_file)
            
            # 清理WAV文件
            threading.Timer(1.0, self.safe_remove_file, args=(wav_file,)).start()
            
            return success
            
        except subprocess.CalledProcessError as e:
            print(f"❌ MP3转WAV失败: {e}")
            return False
        except Exception as e:
            print(f"❌ Linux专用播放失败: {e}")
            # 降级到通用播放方式
            try:
                from xiaoxin2_zh import play_mp3_audio
                return play_mp3_audio(audio_file, "tts")
            except:
                return False
    
    def safe_remove_file(self, filename: str):
        """安全删除文件"""
        try:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"🧹 清理临时文件: {filename}")
        except Exception as e:
            print(f"⚠️ 清理文件失败: {e}")
    
    def cleanup_temp_files(self, file_list: list):
        """清理临时文件"""
        for filename in file_list:
            self.safe_remove_file(filename)
    
    def play_streaming_text(self, text_iterator: Iterator[str]) -> bool:
        """播放流式文本（支持唤醒词中断）"""
        if self.is_playing:
            print("⚠️ 已有播放任务在进行")
            return False
        
        # 请求音频权限
        if not request_audio_access(AudioPriority.TTS, "流式TTS"):
            print("⚠️ 无法获取音频播放权限")
            return False
        
        # 导入音频会话管理器
        from audio_session_manager import get_audio_session_manager
        session_manager = get_audio_session_manager()
        
        try:
            print("🎵 开始流式语音合成和播放")
            
            # 启动播放会话
            session_manager.start_playback("tts")
            
            # 重置状态
            self.interrupt_flag = False
            self.is_playing = True
            
            # 清空队列
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            # 启动合成线程
            self.synthesis_thread = threading.Thread(
                target=self.synthesis_worker,
                args=(text_iterator,),
                daemon=True
            )
            self.synthesis_thread.start()
            
            # 启动播放线程
            self.playback_thread = threading.Thread(
                target=self.playback_worker,
                daemon=True
            )
            self.playback_thread.start()
            
            # 在独立线程中等待播放完成，同时监控中断信号
            def monitor_playback():
                """监控播放状态，支持中断"""
                check_interval = 0.05  # 更频繁的检查，提高响应速度
                max_wait_time = 30  # 最大等待时间
                waited_time = 0

                while self.is_playing and not self.interrupt_flag and waited_time < max_wait_time:
                    # 检查全局中断标志
                    try:
                        import xiaoxin2_zh
                        if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                            print("🛑 检测到全局TTS中断标志，停止监控")
                            self.interrupt_flag = True
                            break
                    except:
                        pass

                    time.sleep(check_interval)
                    waited_time += check_interval

                if self.interrupt_flag:
                    print("🛑 流式播放被唤醒词中断")
                    return False

                if waited_time >= max_wait_time:
                    print("⏰ 流式播放监控超时")
                    self.interrupt_flag = True
                    return False

                # 等待播放线程完成
                if self.playback_thread and self.playback_thread.is_alive():
                    self.playback_thread.join(timeout=5)  # 减少等待时间
                    if self.playback_thread.is_alive():
                        print("⚠️ 播放线程未能及时结束")
                        return False

                return True
            
            # 执行监控
            success = monitor_playback()
            
            if success and not self.interrupt_flag:
                print("✅ 流式语音播放完成")
                return True
            else:
                print("🛑 流式语音播放被中断")
                return False
            
        except Exception as e:
            print(f"❌ 流式语音播放异常: {e}")
            return False
        
        finally:
            # 🔧 关键修复：确保立即释放权限和会话
            print("🔧 [流式TTS] 开始清理资源...")
            
            # 1. 立即设置播放状态为False
            self.is_playing = False

            # 1.5. 重置中断标志，为下次播放做准备
            self.interrupt_flag = False
            
            # 2. 立即结束播放会话
            try:
                session_manager.finish_playback("tts")
                print("✅ [流式TTS] 音频会话已结束")
            except Exception as e:
                print(f"⚠️ [流式TTS] 结束音频会话失败: {e}")
            
            # 3. 立即释放TTS权限
            try:
                release_audio_access(AudioPriority.TTS, "流式TTS")
                print("✅ [流式TTS] TTS权限已释放")
            except Exception as e:
                print(f"⚠️ [流式TTS] 释放TTS权限失败: {e}")
            
            # 4. 确保权限管理器状态更新
            try:
                from audio_priority_manager import get_audio_manager
                audio_manager = get_audio_manager()
                current_status = audio_manager.get_status_info()
                print(f"🔍 [流式TTS] 权限释放后状态: {current_status}")
            except Exception as e:
                print(f"⚠️ [流式TTS] 获取权限状态失败: {e}")
            
            print("🏁 [流式TTS] 资源清理完成")
    
    def interrupt(self):
        """中断流式播放"""
        print("🛑 流式TTS播放被中断")
        self.interrupt_flag = True
        
        # 🔧 关键修复：强力停止合成线程
        if hasattr(self, 'synthesis_thread') and self.synthesis_thread and self.synthesis_thread.is_alive():
            print("🛑 [流式TTS中断] 强制停止合成线程")
            try:
                # 给合成线程0.2秒时间自然停止
                self.synthesis_thread.join(timeout=0.2)
                if self.synthesis_thread.is_alive():
                    print("⚠️ [流式TTS中断] 合成线程未能自然停止，将被强制终止")
                    # 注意：Python没有安全的强制终止线程方法，但我们可以确保它不再产生输出
                    # 通过设置标志并清空队列来达到类似效果
                else:
                    print("✅ [流式TTS中断] 合成线程已自然停止")
            except Exception as e:
                print(f"⚠️ [流式TTS中断] 停止合成线程失败: {e}")
        
        # 🔧 关键修复：立即停止所有音频播放
        try:
            # 1. 停止ALSA TTS播放
            from alsa_cosyvoice_tts import get_alsa_tts
            alsa_tts = get_alsa_tts()
            if alsa_tts:
                alsa_tts.stop_aplay_process()
                print("✅ [流式TTS中断] ALSA TTS播放已停止")
        except Exception as e:
            print(f"⚠️ [流式TTS中断] 停止ALSA TTS失败: {e}")
        
        # 2. 清空音频队列
        try:
            while not self.audio_queue.empty():
                self.audio_queue.get_nowait()
            print("✅ [流式TTS中断] 音频队列已清空")
        except:
            pass
        
        # 3. 发送中断信号到播放线程
        try:
            self.audio_queue.put(('interrupt', None))
            print("✅ [流式TTS中断] 中断信号已发送")
        except:
            pass
        
        # 4. 立即释放权限
        try:
            from audio_priority_manager import AudioPriority, release_audio_access
            release_audio_access(AudioPriority.TTS, "流式TTS-紧急中断")
            print("✅ [流式TTS中断] TTS权限已紧急释放")
        except Exception as e:
            print(f"⚠️ [流式TTS中断] 释放权限失败: {e}")
        
        # 5. 立即设置播放状态为False
        self.is_playing = False
        print("✅ [流式TTS中断] 播放状态已重置")
        
        # 🔧 关键修复：强制释放音频设备
        try:
            import subprocess
            # 强制杀死所有aplay进程，确保音频设备被释放
            subprocess.run(['pkill', '-f', 'aplay'], check=False, capture_output=True)
            print("✅ [流式TTS中断] 已强制释放音频设备")
            # 短暂等待确保设备完全释放
            import time
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ [流式TTS中断] 强制释放音频设备失败: {e}")
    
    def wait_for_completion(self, timeout: float = 30.0):
        """等待播放完成"""
        start_time = time.time()
        while self.is_playing and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if self.is_playing:
            print("⏰ 等待播放完成超时")
            self.interrupt()

def get_streaming_player() -> StreamingTTSPlayer:
    """获取全局流式播放器实例"""
    global global_streaming_player
    if global_streaming_player is None:
        # 从环境变量获取配置
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not found in environment")
        
        global_streaming_player = StreamingTTSPlayer(api_key)
    
    return global_streaming_player

def create_ai_streaming_generator(client: OpenAI, messages: list, model: str, tools: list = None) -> Iterator[str]:
    """创建AI流式生成器"""
    try:
        print("🚀 开始AI流式生成...")
        
        # 准备消息
        from xiaoxin2_skill import getSystemPrompt
        system_message = {"role": "system", "content": getSystemPrompt()}
        
        # 限制消息历史长度，但确保工具相关消息不被截断
        if len(messages) > 10:
            # 保留最近的对话，但确保包含完整的工具调用序列
            limited_messages = messages[-10:]
            # 检查是否有不完整的工具调用序列
            while (limited_messages and 
                   limited_messages[0].get('role') == 'tool' and 
                   len(messages) > len(limited_messages)):
                # 如果第一条是工具消息，需要包含更多上下文
                limited_messages = messages[-(len(limited_messages) + 2):]
                if len(limited_messages) >= len(messages):
                    break
        else:
            limited_messages = messages
        
        full_messages = [system_message] + limited_messages
        
        # 如果有工具但不是普通对话，直接返回提示
        if tools and any(msg.get('role') == 'tool' for msg in limited_messages):
            print("🔧 检测到工具调用上下文，使用非流式处理")
            yield "正在处理您的请求..."
            return
        
        # 创建流式请求
        stream = client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=0.6,
            max_tokens=500,
            tools=tools,
            tool_choice="auto" if tools else None,
            stream=True,
            timeout=30
        )
        
        current_sentence = ""
        has_tool_calls = False
        
        for chunk in stream:
            # 检查是否有工具调用
            if chunk.choices[0].delta.tool_calls:
                has_tool_calls = True
                print("🔧 检测到工具调用，切换到非流式模式")
                yield "正在为您查询相关信息..."
                break
            
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                current_sentence += content
                
                # 检查是否完成一个句子
                if re.search(r'[。！？.!?，,；;：:]', content):
                    if current_sentence.strip():
                        yield current_sentence.strip()
                        current_sentence = ""
        
        # 输出剩余内容（如果没有工具调用）
        if not has_tool_calls and current_sentence.strip():
            yield current_sentence.strip()
        
        if not has_tool_calls:
            print("\n✅ AI流式生成完成")
        else:
            print("🔧 切换到工具处理模式")
        
    except Exception as e:
        print(f"\n❌ AI流式生成异常: {e}")
        # 返回错误消息
        yield "抱歉，我遇到了一些技术问题，请稍后再试。"

def streaming_text_to_speech(ai_response_text: str) -> bool:
    """
    流式文本转语音（兼容现有接口）
    
    Args:
        ai_response_text: AI回复文本
        
    Returns:
        bool: 播放是否成功
    """
    try:
        player = get_streaming_player()
        
        # 将文本分割成句子
        sentences = player.split_text_by_sentences(ai_response_text)
        
        def text_generator():
            for sentence in sentences:
                yield sentence
        
        return player.play_streaming_text(text_generator())
        
    except Exception as e:
        print(f"❌ 流式语音合成失败: {e}")
        return False

def streaming_ai_conversation(client: OpenAI, messages: list, model: str, tools: list = None) -> bool:
    """
    流式AI对话（边生成边语音合成）
    
    Args:
        client: OpenAI客户端
        messages: 对话消息列表
        model: 模型名称
        tools: 工具列表
        
    Returns:
        bool: 对话是否成功
    """
    try:
        print("🎭 开始流式AI对话...")
        
        # 获取流式播放器
        player = get_streaming_player()
        
        # 创建AI文本生成器
        text_generator = create_ai_streaming_generator(client, messages, model, tools)
        
        # 开始流式播放
        success = player.play_streaming_text(text_generator)
        
        if success:
            print("✅ 流式AI对话完成")
        else:
            print("❌ 流式AI对话失败")
        
        return success
        
    except Exception as e:
        print(f"❌ 流式AI对话异常: {e}")
        return False

def streaming_ai_conversation_with_full_response(client: OpenAI, messages: list, model: str, tools: list = None) -> Tuple[bool, str]:
    """
    流式AI对话，返回完整回复文本
    
    Args:
        client: OpenAI客户端
        messages: 对话消息列表
        model: 模型名称
        tools: 工具列表
        
    Returns:
        tuple[bool, str]: (成功标志, 完整回复文本)
    """
    try:
        print("🎭 开始流式AI对话...")
        
        # 检查是否包含工具调用
        if tools:
            print("🔧 检测到工具配置，使用工具处理流程")
            try:
                # 如果有工具，先用传统方式获取完整响应处理工具调用
                full_response = handle_tools_and_get_response(client, messages, model, tools)
                if full_response:
                    print(f"🔧 工具处理完成，回复长度: {len(full_response)} 字符")
                    # 然后流式播放最终回复
                    success = streaming_text_to_speech(full_response)
                    return success, full_response
                else:
                    print("❌ 工具调用未返回有效回复，降级到普通对话")
                    # 降级到普通流式对话
                    pass
            except Exception as e:
                print(f"❌ 工具处理异常: {e}")
                print("🔄 降级到普通流式对话")
                import traceback
                traceback.print_exc()
                # 降级到普通流式对话
                pass
        
        # 普通对话流式处理
        player = get_streaming_player()
        
        # 收集完整回复文本
        full_response_parts = []
        
        def text_generator_with_collection():
            """生成器，同时收集完整文本"""
            for text_chunk in create_ai_streaming_generator(client, messages, model, tools):
                # 清理文本，移除多余空格和线程ID
                cleaned_chunk = re.sub(r'\[\d+\]', '', text_chunk).strip()
                if cleaned_chunk:
                    full_response_parts.append(cleaned_chunk)
                    yield cleaned_chunk
        
        # 开始流式播放
        success = player.play_streaming_text(text_generator_with_collection())
        
        # 组合完整回复，使用正常连接而不是空格连接
        full_response = "".join(full_response_parts) if full_response_parts else ""
        # 清理多余的空格
        full_response = re.sub(r'\s+', ' ', full_response).strip()
        
        if success:
            print("✅ 流式AI对话完成")
            print(f"📝 完整回复: {full_response[:100]}...")
        else:
            print("❌ 流式AI对话失败")
        
        return success, full_response
        
    except Exception as e:
        print(f"❌ 流式AI对话异常: {e}")
        return False, f"对话异常: {e}"

def handle_tools_and_get_response(client: OpenAI, messages: list, model: str, tools: list) -> str:
    """
    处理工具调用并获取最终回复
    
    Args:
        client: OpenAI客户端
        messages: 消息列表
        model: 模型名称
        tools: 工具列表
        
    Returns:
        str: 最终AI回复文本
    """
    try:
        print("🔧 执行工具调用处理...")
        
        # 避免循环导入，使用全局导入的模块
        import sys
        if 'xiaoxin2_zh' in sys.modules:
            xiaoxin_module = sys.modules['xiaoxin2_zh']
            run_conversation = getattr(xiaoxin_module, 'run_conversation', None)
            
            if run_conversation:
                print("📞 调用run_conversation函数...")
                result = run_conversation(messages, tools)
                print(f"📋 run_conversation返回结果类型: {type(result)}")
                
                # 处理返回结果
                if isinstance(result, dict):
                    content = result.get("content", "")
                    print(f"📝 从字典获取内容: {content[:50]}...")
                    return content if content else "工具调用完成，但无回复内容"
                elif isinstance(result, str):
                    print(f"📝 直接返回字符串: {result[:50]}...")
                    return result
                else:
                    print(f"⚠️ 未知返回类型: {type(result)}, 值: {result}")
                    return str(result) if result else "工具调用处理完成"
            else:
                print("❌ 无法找到run_conversation函数")
                raise ImportError("run_conversation函数不存在")
        else:
            print("❌ xiaoxin2_zh模块未加载")
            raise ImportError("xiaoxin2_zh模块未导入")
        
    except ImportError as e:
        print(f"⚠️ 导入run_conversation失败: {e}")
        print("🔄 降级到简单AI回复")
        return get_simple_ai_response(client, messages, model)
    except Exception as e:
        print(f"❌ 工具处理异常: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 降级到简单AI回复")
        return get_simple_ai_response(client, messages, model)

def get_simple_ai_response(client: OpenAI, messages: list, model: str) -> str:
    """
    获取简单AI回复（无工具调用）
    
    Args:
        client: OpenAI客户端
        messages: 消息列表
        model: 模型名称
        
    Returns:
        str: AI回复文本
    """
    try:
        # 准备消息
        from xiaoxin2_skill import getSystemPrompt
        system_message = {"role": "system", "content": getSystemPrompt()}
        
        # 限制消息历史长度
        limited_messages = messages[-10:] if len(messages) > 10 else messages
        full_messages = [system_message] + limited_messages
        
        # 创建请求
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=0.6,
            max_tokens=500,
            timeout=30
        )
        
        return response.choices[0].message.content or ""
        
    except Exception as e:
        print(f"❌ 简单AI回复异常: {e}")
        return "抱歉，我遇到了技术问题，请稍后再试。"

# 测试函数
def test_streaming_tts():
    """测试流式语音合成"""
    print("🧪 测试流式语音合成")
    
    test_text = """
    你好！这是一个流式语音合成的测试。
    我们将把这段文本分成多个句子。
    每个句子都会被单独合成和播放。
    这样可以显著减少用户等待时间，提升体验。
    """
    
    try:
        player = get_streaming_player()
        sentences = player.split_text_by_sentences(test_text.strip())
        
        print(f"📝 分割成 {len(sentences)} 个句子:")
        for i, sentence in enumerate(sentences, 1):
            print(f"  {i}: {sentence}")
        
        def text_generator():
            for sentence in sentences:
                yield sentence
                time.sleep(0.5)  # 模拟AI生成延迟
        
        player.play_streaming_text(text_generator())
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv("xiaoxin.env")
    
    test_streaming_tts() 