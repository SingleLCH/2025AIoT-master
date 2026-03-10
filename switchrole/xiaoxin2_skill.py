import json, ast
import pygame  
import requests, json
from io import BytesIO 
import tempfile 
import time
import datetime  
import io 
import dateutil.parser  
import locale 
import os
import logging
from dotenv import load_dotenv  
import subprocess
from audio_player import play_audio

logger = logging.getLogger(__name__)  

load_dotenv("xiaoxin.env")  
quitReg=False
pause=False
playing=False
def NewContent(content):
    # 获取当前日期和时间  
    now = datetime.datetime.now()  

    # 将日期转换为字符串格式，例如："2023年4月10日"  
    date_string = now.strftime("%Y年%m月%d日")  
     
    print(date_string)  
    current_time = now.strftime("%H点%M分%S秒")  
    print(current_time) 
    
    try:
        # 打开文件以追加模式写入  
        file = open(f'{date_string}.md', "a") 
        # 追加内容  
        file.write(f'''
{content} 【记录时间：{current_time}】''')  
        # 关闭文件  
        file.close() 
        return f'日记已添加成功！'
    except Exception as e:  
        return f'日记添加失败！请稍后再试！'
    
fun_newcontent_desc = {
    "type": "function",
    'function':{
        'name': 'NewContent',
        'description': '添加内容到日记',
        'parameters': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': '用户提供的日记内容,内容可以是markdown格式的任何文本。注意：只需要增量内容，不要重复内容。'
                },
            },
            'required': ['content']
        }
    }
}
def playmusic(song_name):
    """
    播放音乐（修复版：等待TTS播放完成后再播放音乐）
    
    Args:
        song_name: 歌曲名称
    """
    print(f"🎵 开始播放音乐: {song_name}")
    
    # 🔧 关键修复：等待TTS播放完成后再播放音乐
    try:
        from audio_priority_manager import get_audio_manager, AudioPriority
        audio_manager = get_audio_manager()
        
        # 检查当前权限状态
        current_priority = audio_manager.get_current_priority()
        current_status = audio_manager.get_status_info()
        print(f"🔍 播放音乐前音频状态: {current_status}")
        
        # 如果当前是TTS权限，等待TTS播放完成
        if current_priority == AudioPriority.TTS:
            print(f"⏳ 等待TTS播放完成...")
            max_wait_time = 40  # 最多等待40秒
            wait_interval = 0.3
            waited_time = 0
            
            while waited_time < max_wait_time:
                current_priority = audio_manager.get_current_priority()
                if current_priority != AudioPriority.TTS:
                    print(f"✅ TTS播放完成，可以播放音乐 (等待时间: {waited_time:.1f}s)")
                    break
                
                time.sleep(wait_interval)
                waited_time += wait_interval
                
                # 每5秒打印一次状态
                if int(waited_time * 3) % 15 == 0:
                    print(f"⏳ 继续等待TTS播放完成... ({waited_time:.1f}s/{max_wait_time}s)")
            
            if waited_time >= max_wait_time:
                print(f"⚠️ 等待TTS播放完成超时，强制继续播放音乐")
        
        # 如果当前是WAKE_WORD权限，临时释放以支持音乐播放
        elif current_priority == AudioPriority.WAKE_WORD:
            print(f"🔄 播放音乐前临时释放WAKE_WORD权限")
            from audio_priority_manager import release_audio_access
            release_audio_access(AudioPriority.WAKE_WORD, "临时释放给音乐播放")
            print(f"✅ WAKE_WORD权限已临时释放，音乐播放器可以工作")
        
    except Exception as e:
        print(f"⚠️ 音频权限管理失败: {e}")
    
    # 🔧 搜索音乐
    try:
        from netease_music_api import search_music
        music_results = search_music(song_name)
        
        if music_results and 'result' in music_results and music_results['result'].get('songCount', 0) > 0:
            songs = music_results['result']['songs']
            song_title = songs[0].get('name', song_name)
            print(f"🎵 找到音乐: {song_title}")

            # 🔧 先播放TTS提示，然后再播放音乐
            tts_message = f"正在为您播放{song_title}"
            print(f"🎤 播放TTS提示: {tts_message}")

            # 🔧 修复：延迟启动音乐线程，确保TTS先开始播放
            import threading
            import time
            
            def delayed_music_playback():
                """延迟启动音乐播放，确保TTS先播放"""
                # 等待TTS开始播放和权限获取
                time.sleep(2.0)  # 给TTS足够时间获取权限和开始播放
                print(f"🎵 延迟后启动音乐播放...")
                downloadAndPlayMusic(music_results, 0, len(tts_message))
            
            music_thread = threading.Thread(
                target=delayed_music_playback,
                daemon=True
            )
            music_thread.start()

            print(f"✅ 音乐播放线程已启动（延迟模式）")
            return tts_message
        else:
            print(f"❌ 未找到音乐: {song_name}")
            return f"抱歉，没有找到《{song_name}》这首歌"
            
    except Exception as e:
        print(f"❌ 搜索音乐失败: {e}")
        return f"抱歉，搜索音乐时出现了问题"

def downloadAndPlayMusic(music_json, index, tts_text_length=0):
    """
    下载并播放音乐（前台播放版本，支持可中断）
    
    Args:
        music_json: 音乐搜索结果JSON
        index: 歌曲索引
        tts_text_length: TTS文本长度，用于估算播放时间
    """
    global playing, pause
    from audio_priority_manager import AudioPriority, request_audio_access, release_audio_access
    
    # 动态导入音频播放函数，避免循环导入问题
    try:
        # 先尝试从已经导入的模块中获取
        import sys
        if 'xiaoxin2_zh' in sys.modules:
            xiaoxin2_zh = sys.modules['xiaoxin2_zh']
        else:
            # 如果没有导入，我们直接使用本地的播放功能
            xiaoxin2_zh = None
    except Exception as import_error:
        print(f"⚠️ 导入xiaoxin2_zh模块出错: {import_error}")
        xiaoxin2_zh = None
    
    print(f"🎵 downloadAndPlayMusic 函数开始执行，index: {index}")
    
    # 🔧 关键修复：在开始下载前检查中断标志
    if xiaoxin2_zh and hasattr(xiaoxin2_zh, 'tts_interrupt_flag') and xiaoxin2_zh.tts_interrupt_flag:
        print(f"🛑 检测到TTS中断标志，音乐播放被取消")
        return False
    
    # 🔧 优化：智能权限等待，减少固定延迟
    import time
    print(f"🔍 检查TTS权限状态...")
    
    # 获取音频管理器并立即检查权限状态
    from audio_priority_manager import get_audio_manager, AudioPriority
    audio_manager = get_audio_manager()
    
    # 🔧 立即检查当前权限状态
    current_priority = audio_manager.get_current_priority()
    print(f"🔍 当前音频权限: {current_priority.name if current_priority else 'None'}")
    
    # 🔧 关键修复：主动释放WAKE_WORD权限，确保音乐播放器可以工作
    if current_priority == AudioPriority.WAKE_WORD:
        print(f"🔄 检测到WAKE_WORD权限占用，主动释放以支持音乐播放")
        from audio_priority_manager import release_audio_access
        release_audio_access(AudioPriority.WAKE_WORD, "释放给音乐播放")
        print(f"✅ WAKE_WORD权限已释放，音乐播放器可以工作")
    
    # 如果当前没有TTS权限占用，直接尝试获取音乐权限
    if current_priority is None or current_priority not in [AudioPriority.TTS]:
        print(f"✅ TTS权限已释放，直接尝试获取音乐权限")
    else:
        print(f"⏳ TTS权限仍被占用，等待释放...")
        
        # 🔧 修复：优化TTS等待逻辑，更准确地预估等待时间
        if tts_text_length > 0:
            # 根据中文TTS语速（约每秒3-4个字）预估播放时间
            estimated_tts_duration = max(3, tts_text_length / 3.0)  # 更保守的估算
            # 加上合成时间（约2-3秒）
            estimated_wait = estimated_tts_duration + 3
            
            print(f"⏳ 预估TTS播放时间: {estimated_tts_duration:.1f}秒，总等待: {estimated_wait:.1f}秒")
        else:
            estimated_wait = 8  # 默认等待时间
        
        print(f"⏳ 智能等待 {estimated_wait:.1f} 秒让TTS完成播放...")
        time.sleep(estimated_wait)
        
        # 然后开始实时监听TTS权限释放
        max_wait_time = 30  # 最多等待30秒
        check_interval = 0.1  # 高频检查（100ms一次）
        waited_time = 0
        
        print(f"🔍 开始实时监听TTS权限释放状态...")
        
        while waited_time < max_wait_time:
            # 🔧 优先检查中断标志
            if xiaoxin2_zh and hasattr(xiaoxin2_zh, 'tts_interrupt_flag') and xiaoxin2_zh.tts_interrupt_flag:
                print(f"🛑 检测到唤醒中断，音乐播放被取消")
                return False
            
            # 检查TTS权限是否释放
            current_priority = audio_manager.get_current_priority()
            if current_priority is None or current_priority != AudioPriority.TTS:
                print(f"✅ TTS权限已释放 (实际等待时间: {waited_time:.1f}秒)")
                break
            
            time.sleep(check_interval)
            waited_time += check_interval
            
            # 每3秒打印一次状态
            if int(waited_time * 10) % 30 == 0:  
                print(f"⏳ 继续等待TTS播放完成... ({waited_time:.1f}s/{max_wait_time}s)")
        
        if waited_time >= max_wait_time:
            print(f"⚠️ 等待TTS权限释放超时，强制开始音乐播放")
    
    # 🔧 在获取音乐权限前，再次检查并释放WAKE_WORD权限
    current_priority = audio_manager.get_current_priority()
    if current_priority == AudioPriority.WAKE_WORD:
        print(f"🔄 播放前再次检测到WAKE_WORD权限占用，主动释放")
        from audio_priority_manager import release_audio_access
        release_audio_access(AudioPriority.WAKE_WORD, "音乐播放前释放")
        print(f"✅ WAKE_WORD权限已释放，准备获取音乐权限")
        # 短暂等待确保权限释放完成
        time.sleep(0.1)
    
    # 现在尝试获取音乐播放权限
    if not request_audio_access(AudioPriority.MUSIC, "音乐播放器"):
        print(f"❌ 无法获得音乐播放权限")
        return False
    
    print(f"✅ 成功获取音乐播放权限")
    
    # 🔧 获取权限后再次检查中断标志
    if xiaoxin2_zh and hasattr(xiaoxin2_zh, 'tts_interrupt_flag') and xiaoxin2_zh.tts_interrupt_flag:
        print(f"🛑 获取权限后检测到中断，释放权限并取消音乐播放")
        release_audio_access(AudioPriority.MUSIC, "音乐播放器")
        return False
    
    try:
        count = music_json["result"]["songCount"]
        if index >= count:
            playing = False
            release_audio_access(AudioPriority.MUSIC, "音乐播放器")
            return False
            
        songid = music_json["result"]["songs"][index]["id"]
        url = 'http://music.163.com/song/media/outer/url?id=%s.mp3' % songid
        
        print(f"🎵 开始下载音乐 ID: {songid}")
        
        # 🔧 下载前再次检查中断标志
        if xiaoxin2_zh and hasattr(xiaoxin2_zh, 'tts_interrupt_flag') and xiaoxin2_zh.tts_interrupt_flag:
            print(f"🛑 下载前检测到中断，取消下载")
            release_audio_access(AudioPriority.MUSIC, "音乐播放器")
            return False
        
        response = requests.get(url, timeout=10)
        
        # 🔧 增强音频下载验证
        if response.status_code != 200:
            print(f"❌ 下载失败，HTTP状态码: {response.status_code}")
            index += 1
            release_audio_access(AudioPriority.MUSIC, "音乐播放器")
            return downloadAndPlayMusic(music_json, index)
        
        if len(response.content) < 10000:  # 增加最小文件大小要求
            print(f"❌ 下载的音频文件太小: {len(response.content)} bytes，可能是无效链接")
            index += 1
            release_audio_access(AudioPriority.MUSIC, "音乐播放器")
            return downloadAndPlayMusic(music_json, index)
        
        # 🔧 检查是否是HTML错误页面（网易云有时返回错误页面）
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type.lower():
            print(f"❌ 服务器返回HTML页面而非音频文件，可能是版权保护")
            index += 1
            release_audio_access(AudioPriority.MUSIC, "音乐播放器")
            return downloadAndPlayMusic(music_json, index)
        
        # 🔧 检查文件头是否是有效的MP3
        if not response.content.startswith(b'ID3') and not response.content.startswith(b'\xff\xfb'):
            print(f"❌ 下载的文件不是有效的MP3格式")
            # 打印前100字节用于调试
            print(f"🔍 文件头: {response.content[:100]}")
            index += 1
            release_audio_access(AudioPriority.MUSIC, "音乐播放器")
            return downloadAndPlayMusic(music_json, index)
        
        # 保存音频文件
        import time
        timestamp = int(time.time())
        temp_mp3_file = f"music_{timestamp}.mp3"
        
        with open(temp_mp3_file, 'wb') as temp_file:
            temp_file.write(response.content)
        print(f"✅ 音乐文件下载完成: {temp_mp3_file}")
        
        # 设置音乐播放状态
        if xiaoxin2_zh:
            xiaoxin2_zh.music_playing = True
            xiaoxin2_zh.music_paused = False
        playing = True
        pause = False
        
        # 🔧 前台播放音乐（阻塞播放，支持中断检测）- 修复版：只播放一首，不循环
        try:
            print(f"🎵 开始前台播放音乐: {temp_mp3_file}")
            
            # 🔧 播放前最后一次检查中断标志
            if xiaoxin2_zh and hasattr(xiaoxin2_zh, 'tts_interrupt_flag') and xiaoxin2_zh.tts_interrupt_flag:
                print(f"🛑 播放前检测到中断，停止播放")
                # 清理文件和权限
                try:
                    import os
                    if os.path.exists(temp_mp3_file):
                        os.remove(temp_mp3_file)
                        print(f"🗑️ 已清理临时文件: {temp_mp3_file}")
                except:
                    pass
                release_audio_access(AudioPriority.MUSIC, "音乐播放器")
                return False
            
            if xiaoxin2_zh:
                # 🔧 使用主程序的阻塞播放系统，支持中断检测
                print(f"🎵 使用主程序阻塞播放系统: {temp_mp3_file}")
                success = xiaoxin2_zh.play_mp3_audio_blocking_with_interrupt(temp_mp3_file, "music")
                
                if success:
                    print(f"✅ 音乐播放完成: {temp_mp3_file}")
                else:
                    print(f"❌ 音乐播放失败或被中断: {temp_mp3_file}")
                    
            else:
                # 🔧 修复：使用MP3→WAV转换播放（避免pygame问题）
                success = _play_mp3_as_wav_blocking(temp_mp3_file)
                
            # 🔧 重要修改：不管播放成功还是失败，都不尝试下一首歌
            # 用户明确要求只播放一首，不要循环播放
            print(f"🎵 音乐播放结束，不自动播放下一首歌")
            # if not success:
            #     print(f"❌ 音乐播放失败，尝试下一首")
            #     # 播放失败时尝试下一首
            #     downloadAndPlayMusic(music_json, index + 1)
                
        except Exception as e:
            print(f"❌ 音乐播放过程中出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理临时文件
            try:
                import os
                if os.path.exists(temp_mp3_file):
                    os.remove(temp_mp3_file)
                    print(f"🗑️ 已清理临时文件: {temp_mp3_file}")
            except Exception as e:
                print(f"⚠️ 清理临时文件失败: {e}")
            
            # 释放音乐播放权限
            release_audio_access(AudioPriority.MUSIC, "音乐播放器")
            
            # 重置播放状态
            if xiaoxin2_zh:
                xiaoxin2_zh.music_playing = False
                xiaoxin2_zh.music_paused = False
            playing = False
            pause = False
            
            print(f"🎵 音乐播放完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 下载或播放音乐时出错: {e}")
        playing = False
        pause = False
        if xiaoxin2_zh:
            xiaoxin2_zh.music_playing = False
            xiaoxin2_zh.music_paused = False
        release_audio_access(AudioPriority.MUSIC, "音乐播放器")
        
        # 🔧 修改：不尝试下一首，只播放一首歌
        print(f"🎵 音乐播放出错，但不自动尝试下一首")
        # if index + 1 < music_json["result"]["songCount"]:
        #     return downloadAndPlayMusic(music_json, index + 1)
        return False

def _play_mp3_local(mp3_file):
    """
    本地MP3播放函数（跨平台兼容，Linux优先使用专用音频设备）
    """
    import platform
    
    try:
        # 检测操作系统
        is_linux = platform.system().lower() == "linux"
        
        if is_linux:
            # Linux系统：优先使用专用音频播放方式
            print(f"🐧 Linux系统，使用专用音频播放: {mp3_file}")
            return _play_mp3_linux_specific(mp3_file)
        else:
            # Windows/其他系统：使用pygame
            print(f"🖥️ {platform.system()}系统，使用pygame播放: {mp3_file}")
            return _play_mp3_pygame(mp3_file)
            
    except Exception as e:
        print(f"❌ 本地播放失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def _play_mp3_linux_specific(mp3_file):
    """
    Linux专用MP3播放函数 - 🔧 修复版本
    """
    import subprocess
    import os
    import time
    
    try:
        # 转换MP3为WAV格式，使用标准参数
        wav_file = mp3_file.replace('.mp3', '_music.wav')
        print(f"🔄 转换MP3为WAV格式: {wav_file}")
        
        # 🔧 使用统一的WAV转换参数，确保格式匹配
        cmd = [
            'ffmpeg', '-i', mp3_file,
            '-ar', '48000',           # 采样率48000Hz
            '-ac', '2',               # 双声道
            '-sample_fmt', 's16',     # 16位有符号整数
            '-f', 'wav',              # WAV格式
            '-y', wav_file            # 覆盖输出文件
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ MP3转WAV失败: {result.stderr}")
            return False
        
        if not os.path.exists(wav_file):
            print("❌ WAV文件未生成")
            return False
        
        print(f"✅ MP3转WAV成功: {wav_file}")
        
        # 🔧 优先使用主程序的audio_player（阻塞播放）
        try:
            from audio_player import play_audio_blocking
            print("🎵 使用audio_player阻塞播放WAV文件...")
            success = play_audio_blocking(wav_file)
            
            if success:
                print("✅ audio_player阻塞播放成功")
                # 清理临时WAV文件
                try:
                    if os.path.exists(wav_file):
                        os.remove(wav_file)
                        print(f"🗑️ 已清理临时WAV文件: {wav_file}")
                except Exception as cleanup_error:
                    print(f"⚠️ 清理WAV文件失败: {cleanup_error}")
                return True
            else:
                print("⚠️ audio_player阻塞播放失败")
        except Exception as audio_player_error:
            print(f"⚠️ audio_player异常: {audio_player_error}")
        
        # 备用方案：使用aplay播放，使用正确的格式参数
        print("🎵 使用aplay播放WAV文件...")
        
        # 🔧 使用标准的aplay参数，不指定格式（让aplay自动检测）
        aplay_cmd = ['aplay', wav_file]
        
        print(f"🎵 执行播放命令: {' '.join(aplay_cmd)}")
        result = subprocess.run(aplay_cmd, timeout=300, capture_output=True, text=True)  # 5分钟超时
        
        success = result.returncode == 0
        
        if not success:
            print(f"❌ aplay播放失败，返回码: {result.returncode}")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
        
        # 清理临时WAV文件
        try:
            if os.path.exists(wav_file):
                os.remove(wav_file)
                print(f"🗑️ 已清理临时WAV文件: {wav_file}")
        except Exception as cleanup_error:
            print(f"⚠️ 清理WAV文件失败: {cleanup_error}")
        
        if success:
            print("✅ aplay播放完成")
        else:
            print("❌ aplay播放失败")
        
        return success
        
    except Exception as e:
        print(f"❌ Linux音乐播放失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def _find_lahainayupikiot_card():
    """查找lahainayupikiot声卡索引"""
    import subprocess
    
    try:
        result = subprocess.run(['cat', '/proc/asound/cards'], 
                              capture_output=True, text=True, timeout=5)
        
        lines = result.stdout.split('\n')
        for line in lines:
            if 'lahainayupikiot' in line.lower():
                # 提取声卡索引
                parts = line.strip().split()
                if parts:
                    index_str = parts[0]
                    try:
                        return int(index_str)
                    except ValueError:
                        continue
        
        print("⚠️ 未找到lahainayupikiot声卡")
        return None
        
    except Exception as e:
        print(f"⚠️ 查找声卡失败: {e}")
        return None

def _play_mp3_pygame(mp3_file):
    """
    使用pygame播放MP3文件（Windows/其他系统）
    """
    try:
        import pygame
        import time
        
        print(f"🔊 使用pygame播放: {mp3_file}")
        
        # 初始化pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # 停止当前播放
        pygame.mixer.stop()
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        # 等待mixer完全停止
        time.sleep(0.1)
        
        # 加载并播放音频文件
        pygame.mixer.music.load(mp3_file)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        # 确保完全停止
        pygame.mixer.music.stop()
        time.sleep(0.2)
        
        print(f"✅ pygame播放完成: {mp3_file}")
        return True
        
    except Exception as e:
        print(f"❌ pygame播放失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 确保停止播放
        try:
            import pygame
            pygame.mixer.music.stop()
        except:
            pass
        
        return False

def _play_mp3_local_blocking(mp3_file):
    """
    本地阻塞播放MP3文件的备用方案（修复pygame静态TLS问题）
    
    Args:
        mp3_file: MP3文件路径
    
    Returns:
        bool: 播放是否成功
    """
    try:
        print(f"🎵 使用本地方案阻塞播放: {mp3_file}")
        
        # 🔧 修复pygame静态TLS问题：优先使用系统音频工具
        success = _play_mp3_with_system_tools(mp3_file)
        if success:
            return True
        
        # 如果系统工具失败，再尝试pygame（可能遇到TLS问题）
        print("⚠️ 系统音频工具失败，尝试pygame...")
        
        import pygame
        import time
        
        # 初始化pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # 停止当前播放的所有音频
        pygame.mixer.stop()
        
        # 确保完全释放之前的资源
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        # 等待mixer完全停止
        time.sleep(0.1)
        
        # 加载并播放音频文件
        pygame.mixer.music.load(mp3_file)
        pygame.mixer.music.play()
        
        print(f"🎵 开始播放，等待完成...")
        
        # 等待播放完成，同时检查中断标志
        while pygame.mixer.music.get_busy():
            # 检查全局中断标志
            try:
                import xiaoxin2_zh
                if getattr(xiaoxin2_zh, 'tts_interrupt_flag', False):
                    print(f"🛑 本地播放被唤醒中断: {mp3_file}")
                    pygame.mixer.music.stop()
                    time.sleep(0.1)
                    return False
            except:
                pass  # 忽略导入错误
            
            time.sleep(0.1)
        
        # 播放完成后确保完全停止和清理状态
        pygame.mixer.music.stop()
        time.sleep(0.2)  # 等待完全释放
        
        print(f"✅ 本地播放完成: {mp3_file}")
        return True
        
    except Exception as e:
        print(f"❌ 本地播放失败: {e}")
        
        # 确保停止播放
        try:
            pygame.mixer.music.stop()
            time.sleep(0.1)
        except:
            pass
        
        return False

def _play_mp3_with_system_tools(mp3_file):
    """
    使用系统音频工具播放MP3（避免pygame TLS问题）
    
    Args:
        mp3_file: MP3文件路径
    
    Returns:
        bool: 播放是否成功
    """
    try:
        print(f"🔧 尝试系统音频工具播放: {mp3_file}")
        
        import subprocess
        import platform
        import time
        
        # 检查中断标志的辅助函数
        def check_interrupt():
            try:
                import xiaoxin2_zh
                return getattr(xiaoxin2_zh, 'tts_interrupt_flag', False)
            except:
                return False
        
        # 根据系统选择合适的播放工具
        system = platform.system().lower()
        
        if system == "linux":
            # Linux: 尝试多种播放工具
            commands = [
                ["ffplay", "-nodisp", "-autoexit", mp3_file],  # ffmpeg的播放器
                ["mpg123", "-q", mp3_file],                    # 专用MP3播放器
                ["cvlc", "--intf", "dummy", "--play-and-exit", mp3_file],  # VLC
                ["aplay", mp3_file]  # ALSA播放器（如果是WAV格式）
            ]
            
            for cmd in commands:
                try:
                    print(f"🔧 尝试命令: {' '.join(cmd)}")
                    
                    # 检查命令是否可用
                    check_cmd = ["which", cmd[0]]
                    result = subprocess.run(check_cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"⚠️ {cmd[0]} 命令不可用，跳过")
                        continue
                    
                    # 启动播放进程
                    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # 等待播放完成，同时检查中断
                    while process.poll() is None:
                        if check_interrupt():
                            print(f"🛑 系统工具播放被中断: {mp3_file}")
                            process.terminate()
                            try:
                                process.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                            return False
                        time.sleep(0.1)
                    
                    # 检查播放结果
                    if process.returncode == 0:
                        print(f"✅ 系统工具播放完成: {cmd[0]}")
                        return True
                    else:
                        print(f"❌ {cmd[0]} 播放失败，返回码: {process.returncode}")
                        
                except FileNotFoundError:
                    print(f"⚠️ {cmd[0]} 命令未找到")
                    continue
                except Exception as e:
                    print(f"❌ {cmd[0]} 播放异常: {e}")
                    continue
            
        elif system == "windows":
            # Windows: 使用Windows Media Player命令行
            try:
                cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{mp3_file}').PlaySync()"]
                process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                while process.poll() is None:
                    if check_interrupt():
                        print(f"🛑 Windows播放被中断: {mp3_file}")
                        process.terminate()
                        return False
                    time.sleep(0.1)
                
                if process.returncode == 0:
                    print(f"✅ Windows播放完成")
                    return True
                    
            except Exception as e:
                print(f"❌ Windows播放失败: {e}")
        
        elif system == "darwin":  # macOS
            try:
                cmd = ["afplay", mp3_file]
                process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                while process.poll() is None:
                    if check_interrupt():
                        print(f"🛑 macOS播放被中断: {mp3_file}")
                        process.terminate()
                        return False
                    time.sleep(0.1)
                
                if process.returncode == 0:
                    print(f"✅ macOS播放完成")
                    return True
                    
            except Exception as e:
                print(f"❌ macOS播放失败: {e}")
        
        print(f"❌ 所有系统音频工具都失败")
        return False
        
    except Exception as e:
        print(f"❌ 系统工具播放异常: {e}")
        return False

def _play_mp3_as_wav_blocking(mp3_file):
    """
    将MP3转换为WAV并播放（解决pygame板子兼容性问题）
    
    Args:
        mp3_file: MP3文件路径
    
    Returns:
        bool: 播放是否成功
    """
    try:
        print(f"🔧 使用MP3→WAV转换播放: {mp3_file}")
        
        import subprocess
        import tempfile
        import time
        
        # 检查中断标志的辅助函数
        def check_interrupt():
            try:
                import xiaoxin2_zh
                return getattr(xiaoxin2_zh, 'tts_interrupt_flag', False)
            except:
                return False
        
        # 生成临时WAV文件
        temp_wav = f"{mp3_file}.wav"
        
        # 🔧 修复：使用正确的WAV格式参数，匹配audio_player.py的期望格式
        print(f"🔄 转换MP3为WAV: {temp_wav}")
        cmd = ['ffmpeg', '-i', mp3_file, 
               '-ar', '48000',           # 采样率48000Hz
               '-ac', '2',               # 双声道
               '-sample_fmt', 's16',     # 16位有符号整数
               '-f', 'wav',              # WAV格式
               '-y', temp_wav]           # 覆盖输出文件
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"❌ MP3转WAV失败: {result.stderr}")
                return False
            
            print(f"✅ MP3转WAV成功: {temp_wav}")
            
        except subprocess.TimeoutExpired:
            print("❌ MP3转WAV超时")
            return False
        except FileNotFoundError:
            print("❌ ffmpeg命令不可用，尝试其他转换方法...")
            
            # 尝试使用pydub作为备用方案
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(mp3_file)
                audio.export(temp_wav, format="wav")
                print(f"✅ 使用pydub转换成功: {temp_wav}")
            except ImportError:
                print("❌ pydub不可用，无法转换MP3")
                return False
            except Exception as e:
                print(f"❌ pydub转换失败: {e}")
                return False
        
        # 检查转换后的文件是否存在
        if not os.path.exists(temp_wav):
            print(f"❌ 转换后的WAV文件不存在: {temp_wav}")
            return False
        
        # 播放前检查中断
        if check_interrupt():
            print(f"🛑 播放前检测到中断，清理文件")
            try:
                os.remove(temp_wav)
            except:
                pass
            return False
        
        # 使用现有的音频播放器播放WAV文件
        print(f"🔊 开始播放WAV文件: {temp_wav}")
        
        from audio_player import play_audio_blocking
        success = play_audio_blocking(temp_wav)
        
        if success:
            print(f"✅ WAV文件播放完成: {temp_wav}")
        else:
            print(f"❌ WAV文件播放失败: {temp_wav}")
        
        # 清理临时WAV文件
        try:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
                print(f"🗑️ 已清理临时WAV文件: {temp_wav}")
        except Exception as e:
            print(f"⚠️ 清理WAV文件失败: {e}")
        
        return success
        
    except Exception as e:
        print(f"❌ MP3→WAV播放异常: {e}")
        
        # 确保清理临时文件
        try:
            temp_wav = f"{mp3_file}.wav"
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
        except:
            pass
        
        return False

# 已删除重复的downloadAndPlay函数，使用downloadAndPlayMusic替代
        
    
fun_playmusic_desc = {
    "type": "function",
    'function':{
        'name': 'playmusic',
        'description': '在线搜索并播放音乐歌曲。只有当用户明确要求播放音乐、听歌或指定歌曲名称时才使用此功能。不要在用户要求讲故事、聊天或其他非音乐相关请求时调用此功能。',
        'parameters': {
            'type': 'object',
            'properties': {
                'song_name': {
                    'type': 'string',
                    'description': '要播放的歌曲名称，如"晴天"、"青花瓷"等。必须是用户明确指定的歌曲名。'
                },
            },
            'required': ['song_name']
        }
    }
}
def stopplay():
    global playing, pause 
    
    from audio_priority_manager import AudioPriority, release_audio_access
    from audio_player import stop_all_audio
    
    # 停止所有音频播放进程
    stopped_count = stop_all_audio()
    
    # 释放音乐播放权限
    release_audio_access(AudioPriority.MUSIC, "停止播放")
    
    playing = False
    pause = False
    
    if stopped_count > 0:
        print(f"已停止 {stopped_count} 个音频播放进程")
        return f"已停止音乐播放。"
    else:
        print("没有正在播放的音频")
        return "当前没有正在播放的音乐。"
    
fun_stopplay_desc = {
    "type": "function",
    'function':{
        'name': 'stopplay',
        'description': '停止播放',
        'parameters': {
            'type': 'object',
            'properties': {

            },
            'required': []
        }
    }
}
# pauseplay和unpauseplay函数已删除
# 原因：当前音频播放器不支持真正的暂停/恢复功能，只是状态标志
# 用户可以通过语音命令"停止播放"和重新"播放音乐"来控制
# isPause和isPlaying函数已删除 - 没有代码调用这些函数

def playTTSAudio(audio_file_path):
    """
    播放TTS生成的音频文件
    
    Args:
        audio_file_path (str): 音频文件路径
        
    Returns:
        str: 播放结果信息
    """
    try:
        success = play_audio(audio_file_path)
        if success:
            return f"音频播放成功: {audio_file_path}"
        else:
            return f"音频播放失败: {audio_file_path}"
    except Exception as e:
        return f"音频播放出错: {str(e)}"

fun_playTTSAudio_desc = {
    "type": "function",
    'function':{
        'name': 'playTTSAudio',
        'description': '播放TTS语音合成生成的音频文件，仅用于播放系统生成的语音回复，不用于播放音乐',
        'parameters': {
            'type': 'object',
            'properties': {
                'audio_file_path': {
                    'type': 'string',
                    'description': 'TTS语音合成生成的音频文件路径，通常是系统回复的.wav文件'
                },
            },
            'required': ['audio_file_path']
        }
    }
}

reminders=[]
def currentDatetime():
    # 获取系统时间并加上8小时
    now = datetime.datetime.now() + datetime.timedelta(hours=8)
    
    # 手动设置星期几的中文映射
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday_chinese = weekdays[now.weekday()]
    
    # 使用安全的格式化方式
    current_datetime = f"{now.year}年{now.month:02d}月{now.day:02d}日 {weekday_chinese} {now.hour:02d}时{now.minute:02d}分{now.second:02d}秒"
    
    print("currentDatetime: "+current_datetime)
    return current_datetime
    
fun_currentDatetime_desc = {
    "type": "function",
    'function':{
        'name': 'currentDatetime',
        'description': '获取现在的日期和时间',
        'parameters': {
            'type': 'object',
            'properties': {

            },
            'required': []
        }
    } 
}
def addReminder(target:str, content: str):  
    reminders.append({'target':target,"content":content})
    print(f"提醒:【{content}】已添加到{target}") 
    return f'定时提醒已添加'
    
tool_addReminder_des={
            "type": "function",
            "function": {
                "name": "addReminder",
                "description": "添加提醒",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "提醒的具体时间，格式为：%Y-%m-%d %H:%M:%S",
                        },
                        "content": {
                            "type": "string",
                            "description": "提醒内容",
                        },
                        
                    },
                    "required": ["target","content"],
                },
            },
        }    
def removeReminder(content: str): 
    global reminders
    hasRemoved=False
    for reminder in reminders:
        if content in reminder["content"]:
            hasRemoved=True
            break
    reminders[:] = [reminder for reminder in reminders if content not in reminder.get('content')]  
    if hasRemoved:        
        print(f"提醒:【{content}】已从提醒列表移除") 
        return f'提醒已从列表移除'
    else:
        print(f"没有找到可移除的提醒！") 
        return f'没有找到可移除的提醒'
    
    
tool_removeReminder_des={
            "type": "function",
            "function": {
                "name": "removeReminder",
                "description": "移除提醒",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "要移除的提醒",
                        },
                        
                    },
                    "required": ["content"],
                },
            },
        } 

 
def checkReminders(feedback):
    global reminders
    # 获取系统时间并加上8小时
    now = datetime.datetime.now() + datetime.timedelta(hours=8)
    #print(reminders)
    #print(now)
    for reminder in reminders:  
        target = dateutil.parser.parse(reminder['target'])  
        if target <= now <= (target + datetime.timedelta(minutes=10)):  
            print(reminder['content'])
            feedback(f"请注意，{reminder['content']}的提醒到时间了。如取消提醒请告诉我。")
            
deploymentModel = None          
def setLLMVersion(deployment="qwen-plus"):
    global deploymentModel
    deploymentModel=deployment
    if deployment=="qwen-max":
        deploymentModel= "qwen-max"  
    elif deployment=="qwen-plus":
        deploymentModel = "qwen-plus"
    elif deployment=="qwen-turbo":
        deploymentModel = "qwen-turbo"
    else:
        deploymentModel = "qwen-plus"  # 默认使用qwen-plus
    return f"大模型已切换为：{deployment}"
        
    
tool_setLLMVersion_des={
            "type": "function",
            "function": {
                "name": "setLLMVersion",
                "description": "切换大模型的版本",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "deployment": {"type": "string", "enum": ["qwen-plus", "qwen-max", "qwen-turbo"]},
                    },
                    "required": ["deployment"],
                },
            },
        }
def Get_Chat_Deployment():
    global deploymentModel
    if not deploymentModel:
        deploymentModel = os.environ["DASHSCOPE_MODEL"]    
    return deploymentModel

checkMessage=False
def CheckMessage(isOpen):
    global checkMessage
    checkMessage=(isOpen==1)
    return "网络唤醒已设置为开启" if isOpen==1 else "网络唤醒已设置为关闭"

tool_CheckMessage_des={
            "type": "function",
            "function": {
                "name": "CheckMessage",
                "description": "将网络唤醒功能设置为打开或关闭",
                "parameters": {
                    "type": "object",
                    "properties": {
                       "isOpen": {"type": "number","description": "网络唤醒（打开）为:1,网络唤醒（关闭）为:0",},
                    },
                    "required": ["isOpen"],
                },
            },
        }
def getCheckMessage():
    global checkMessage
    return checkMessage

isquit=False
def setQuit(isQuit):
    global isquit
    isquit=(isQuit==1)
    return "服务即将退出" if isquit else "继续为您服务"

tool_setQuit_des={
            "type": "function",
            "function": {
                "name": "setQuit",
                "description": "设置是否退出语音助手",
                "parameters": {
                    "type": "object",
                    "properties": {
                       "isQuit": {"type": "number","description": "退出为1,不退出为0",},
                    },
                    "required": ["isQuit"],
                },
            },
        }
def quit():
    global isquit
    print(f"isquit:{isquit}")
    re= True if isquit else False
    isquit=False
    return re

def dismissAssistant():
    """
    退下助手，停止当前对话，返回到唤醒词监听状态
    """
    global playing, pause
    
    # 停止所有音频播放进程
    from audio_player import stop_all_audio
    stopped_count = stop_all_audio()
    
    playing = False
    pause = False
    
    if stopped_count > 0:
        print(f"停止了 {stopped_count} 个音频播放进程，准备退下")
    
    # 设置退出标志，让主循环回到唤醒词监听
    setQuit(1)
    
    return "好的，我先退下了。如需要我，请说'你好广和通'来唤醒我。"

tool_dismissAssistant_des={
    "type": "function",
    "function": {
        "name": "dismissAssistant",
        "description": "让助手退下，停止当前对话，返回到唤醒词监听状态。用于处理'退下'、'退下吧'、'不需要你了'等指令",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}
    

def runInTerminal(script):  
    # 作为字符串传递命令  
    try:  
        output = subprocess.check_output(script, shell=True, stderr=subprocess.STDOUT)  
        result = output.decode('utf-8')
        print(result)  # 需要解码成字符串 
    except subprocess.CalledProcessError as e:  
        print("Command failed with return code", e.returncode)  
        error=e.output.decode('utf-8')
        print("Error output:\n", error)  
        # 打印输出  
        result=f"Command failed with return code: {e.returncode}\nError output:\n{error}"
    return result
    
tool_runInTerminal_des={
            "type": "function",
            "function": {
                "name": "runInTerminal",
                "description": "对Mac电脑进行控制，执行脚本在终端，终端执行的结果是返回值",
                "parameters": {
                    "type": "object",
                    "properties": {
                       "script": {"type": "string","description": "执行的脚本或命令",},
                    },
                    "required": ["script"],
                },
            },
        }
#start switch role skill
tool_switchRole_des={
            "type": "function",
            "function": {
                "name": "switchRole",
                "description": "切换广和通语音助手的角色",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string","description": "切换到的角色名称", "enum": ["日记助手", "音乐助手","系统控制助手","聊天助手","家庭教师"]},
                    },
                    "required": ["role"],
                },
            },
        }


def getTools():
    global tools
    return tools


def switchRole(role):
    global tools,messages
    if role=='日记助手':
        tools=[fun_newcontent_desc,
           fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, fun_playTTSAudio_desc, tool_setLLMVersion_des,tool_CheckMessage_des,tool_switchRole_des,tool_dismissAssistant_des]
        messages=[]
    elif role=='音乐助手':
        tools=[fun_playmusic_desc,fun_stopplay_desc,
        fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, fun_playTTSAudio_desc, tool_setLLMVersion_des,tool_CheckMessage_des,tool_switchRole_des,tool_setQuit_des,tool_dismissAssistant_des]
        messages=[]
    elif role=='系统控制助手':
        tools=[tool_runInTerminal_des, fun_playTTSAudio_desc, tool_setLLMVersion_des,tool_switchRole_des,tool_dismissAssistant_des]
        messages=[]
    elif role=='聊天助手':
        tools=[fun_playTTSAudio_desc, tool_setLLMVersion_des,tool_switchRole_des,tool_restart_self_des,tool_dismissAssistant_des]
        messages=[]
    elif role=='家庭教师':
        tools=[fun_newcontent_desc,
           fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, fun_playTTSAudio_desc, tool_setLLMVersion_des,tool_CheckMessage_des,tool_switchRole_des,tool_setQuit_des,tool_dismissAssistant_des]
        messages=[]
    
    
    if role:
        return f"我现在是你的{role}了！"
    else:
        return "没有找到合适的助手。"
    
#end switch role skill

#start restart self skill
startfile='xiaoxin2_zh.py'
_isrestart=False
def restart_self(mainfile):
    global startfile,_isrestart
    setQuit(1)
    startfile=mainfile
    _isrestart=True
    return "收到，马上就好。"
    
tool_restart_self_des={
            "type": "function",
            "function": {
                "name": "restart_self",
                "description": "开始重启自身，特别指本语音助手重启时使用的方法",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mainfile": {"type": "string","description": "py入口文件，固定为:xiaoxin2_zh.py"},
                    },
                    "required": ["mainfile"],
                },
            },
        }  
def isrestart():
    global startfile,_isrestart
    return _isrestart
def start():
    global startfile,_isrestart
    os.system(f'python {startfile}')  
#end restart self role skill

system_prompt=os.environ.get("sysprompt_zh-CN", "你是一个智能助手，能够帮助用户处理各种任务。")

def getSystemPrompt():
    """获取系统提示词 - 🔧 集成用户记忆的动态人设"""
    try:
        from user_memory import get_current_prompt
        dynamic_prompt = get_current_prompt()
        if dynamic_prompt:
            print(f"🎭 使用动态AI人设提示词")
            return dynamic_prompt
    except Exception as e:
        print(f"⚠️ 获取动态人设失败: {e}")
    
    # 回退到默认提示词
    return system_prompt

# 清除缓存功能
def clear_cache_files():
    """
    清除当前路径下的缓存文件
    自动扫描并删除以cosyvoice开头和music开头的文件
    
    Returns:
        str: 清理结果报告
    """
    import os
    import glob
    
    try:
        print("🧹 开始清理缓存文件...")
        
        # 获取当前路径
        current_path = os.getcwd()
        print(f"📁 扫描路径: {current_path}")
        
        # 扫描以cosyvoice开头的文件
        cosyvoice_files = glob.glob("cosyvoice*")
        
        # 扫描以music开头的文件
        music_files = glob.glob("music*")
        
        # 合并文件列表
        cache_files = cosyvoice_files + music_files
        
        if not cache_files:
            print("✅ 没有找到需要清理的缓存文件")
            return "当前路径下没有找到需要清理的缓存文件（cosyvoice*、music*）"
        
        print(f"🔍 找到 {len(cache_files)} 个缓存文件:")
        for file in cache_files:
            file_size = os.path.getsize(file) if os.path.exists(file) else 0
            print(f"   📄 {file} ({file_size / 1024:.1f} KB)")
        
        # 删除文件
        deleted_count = 0
        deleted_size = 0
        failed_files = []
        
        for file in cache_files:
            try:
                if os.path.exists(file):
                    file_size = os.path.getsize(file)
                    os.remove(file)
                    deleted_count += 1
                    deleted_size += file_size
                    print(f"🗑️ 已删除: {file}")
                else:
                    print(f"⚠️ 文件不存在: {file}")
            except Exception as e:
                failed_files.append(file)
                print(f"❌ 删除失败: {file} - {e}")
        
        # 生成结果报告
        result_lines = []
        result_lines.append(f"🧹 缓存清理完成！")
        result_lines.append(f"📊 清理统计:")
        result_lines.append(f"   ✅ 成功删除: {deleted_count} 个文件")
        result_lines.append(f"   💾 释放空间: {deleted_size / 1024:.1f} KB")
        
        if failed_files:
            result_lines.append(f"   ❌ 删除失败: {len(failed_files)} 个文件")
            for file in failed_files:
                result_lines.append(f"      - {file}")
        
        result_text = "\n".join(result_lines)
        print(result_text)
        
        return result_text
        
    except Exception as e:
        error_msg = f"❌ 清理缓存时发生错误: {str(e)}"
        print(error_msg)
        return error_msg

# 清除缓存功能的工具描述
fun_clear_cache_desc = {
    "type": "function",
    "function": {
        "name": "clear_cache_files",
        "description": "清除当前路径下的缓存文件，包括cosyvoice开头的TTS音频文件和music开头的音乐缓存文件。释放存储空间。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

# 解题功能辅助函数
def parse_problem_request(user_input):
    """
    解析用户的解题请求，提取题目编号和具体要求
    
    Args:
        user_input: 用户的自然语言输入
    
    Returns:
        dict: 包含解析结果的字典
    """
    import re
    
    result = {
        "has_number": False,
        "question_number": None,
        "question_part": None,
        "enhanced_prompt": user_input
    }
    
    # 检测题目编号的各种表达方式
    number_patterns = [
        r'第(\d+)题',
        r'第(\d+)道题',
        r'第([一二三四五六七八九十])题',
        r'第([一二三四五六七八九十])道题',
        r'(\d+)题',
        r'题目(\d+)',
        r'第(\d+)小题',
        r'第(\d+)大题',
        r'第([一二三四五六七八九十])小题',
        r'第([一二三四五六七八九十])大题'
    ]
    
    # 中文数字转阿拉伯数字
    chinese_numbers = {
        '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
        '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'
    }
    
    for pattern in number_patterns:
        match = re.search(pattern, user_input)
        if match:
            number_str = match.group(1)
            # 转换中文数字
            if number_str in chinese_numbers:
                number_str = chinese_numbers[number_str]
            
            result["has_number"] = True
            result["question_number"] = number_str
            
            # 判断是大题还是小题
            if '大题' in match.group(0):
                result["question_part"] = "大题"
            elif '小题' in match.group(0):
                result["question_part"] = "小题"
            
            # 增强提示词
            if result["question_part"]:
                result["enhanced_prompt"] = f"这是一张试卷图片，请找到并解答第{number_str}{result['question_part']}。请详细说明解题思路和步骤。如果图片中没有明确的题目编号，请根据题目在图片中的位置来判断。"
            else:
                result["enhanced_prompt"] = f"这是一张试卷图片，请找到并解答第{number_str}题。请详细说明解题思路和步骤。如果图片中没有明确的题目编号，请根据题目在图片中的位置来判断。"
            break
    
    # 如果没有找到具体题号，但包含解题关键词，增强提示
    if not result["has_number"]:
        solve_keywords = ['解答', '解题', '分析', '计算', '证明', '求解']
        if any(keyword in user_input for keyword in solve_keywords):
            result["enhanced_prompt"] = f"{user_input}。请提供详细的解题步骤和思路分析。"
    
    return result

# 解题功能 - 使用Qwen-Omni模型
def solve_problem(image_path="test.jpg", problem_description=""):
    """
    使用Qwen-Omni模型进行智能解题
    
    Args:
        image_path: 题目图片路径，默认为test.jpg，支持单题或整张试卷
        problem_description: 详细的问题描述，支持指定题目编号、题型要求等
    
    Returns:
        str: 解题结果
        
    示例用法：
        solve_problem("test.jpg", "请解答第3题")
        solve_problem("exam.jpg", "这是一张数学试卷，请帮我解答第二大题")
        solve_problem("physics.jpg", "请分析图片中关于力学的题目，需要详细的解题步骤")
    """
    import base64
    import os
    from openai import OpenAI
    
    try:
        print(f"🤖 开始使用Qwen-Omni解题...")
        print(f"📸 图片路径: {image_path}")
        print(f"📝 问题描述: {problem_description}")
        
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            return f"抱歉，找不到图片文件：{image_path}。请确保图片文件存在。"
        
        # 获取API配置
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return "抱歉，API密钥未配置，无法进行解题。"
        
        # Base64编码图片
        def encode_image(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        
        base64_image = encode_image(image_path)
        
        # 创建OpenAI客户端（使用阿里云DashScope兼容接口）
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 构建消息内容
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        ]
        
        # 智能处理问题描述
        if problem_description.strip():
            # 解析用户的请求，提取题目编号等信息
            parsed_request = parse_problem_request(problem_description)
            prompt_text = parsed_request["enhanced_prompt"]
            
            print(f"📝 解析用户请求:")
            print(f"   原始输入: {problem_description}")
            if parsed_request["has_number"]:
                print(f"   检测到题目编号: 第{parsed_request['question_number']}{parsed_request['question_part'] or '题'}")
            print(f"   增强后提示: {prompt_text}")
        else:
            # 默认通用提示
            prompt_text = "请帮我分析和解答这道题目，请详细说明解题思路和步骤。"
            print(f"📝 使用默认问题描述")
        
        content.insert(0, {
            "type": "text", 
            "text": prompt_text
        })
        
        print(f"🚀 调用qwen-omni-turbo-latest模型...")
        
        # 调用Qwen-Omni模型（使用流式模式）
        completion = client.chat.completions.create(
            model="qwen-omni-turbo-latest",
            messages=[{
                "role": "user",
                "content": content
            }],
            # 只输出文本，不输出音频
            modalities=["text"],
            stream=True,  # 必须使用流式模式
            stream_options={"include_usage": True},
            max_tokens=2000,
            temperature=0.1  # 降低随机性，提高解题准确性
        )
        
        # 获取流式解题结果
        result = ""
        for chunk in completion:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta:
                delta_content = chunk.choices[0].delta.content
                if delta_content:
                    result += delta_content
                    # 显示实时进度
                    if len(result) % 100 == 0:  # 每100个字符显示一次进度
                        print(f"📝 解题进度: {len(result)}字符...")
            elif chunk.usage:
                # 处理使用情况统计
                break
        
        print(f"✅ 解题完成")
        print(f"📄 解题结果: {result[:100]}...")  # 只打印前100个字符
        
        return f"好的，我来帮你解这道题！\n\n{result}"
        
    except Exception as e:
        print(f"❌ 解题过程出错: {e}")
        import traceback
        traceback.print_exc()
        return f"抱歉，解题过程中出现了错误：{str(e)}。请稍后再试。"

# 解题功能的工具描述
fun_solve_problem_desc = {
    "type": "function",
    "function": {
        "name": "solve_problem",
        "description": "使用AI视觉模型解答图片中的题目，支持数学题、物理题、化学题等各种学科题目。可以从整张试卷中解答特定题目。",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string", 
                    "description": "题目图片的文件路径，默认为test.jpg。可以是单题图片或整张试卷图片。",
                    "default": "test.jpg"
                },
                "problem_description": {
                    "type": "string",
                    "description": """详细的问题描述或解题要求。支持以下格式：
                    - 指定题目：'请解答第3题'、'帮我做第五题'、'解答图片中的第一道题'
                    - 题型指定：'请解答这道数学题'、'分析这道物理题的解题思路'
                    - 详细要求：'请详细解答这道关于矩阵的证明题，要包含每一步的推理过程'
                    - 特定部分：'请解答图片上方的选择题'、'帮我解答最后一道大题'
                    - 完整描述：'这是一张数学试卷，请帮我解答第二大题的第一小题，需要详细的计算步骤'
                    如果为空，则使用默认的通用解题提示。""",
                    "default": ""
                }
            },
            "required": ["image_path"]
        }
    }
}

# 初始化消息历史和工具列表
messages=[]

# 🔧 新增：设置控制功能 - 支持AI理解并调用

def _convert_chinese_number(text):
    """将中文数字转换为阿拉伯数字"""
    chinese_nums = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, 
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
        '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
        '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24, '二十五': 25,
        '三十': 30, '四十': 40, '五十': 50, '六十': 60, '七十': 70, '八十': 80, '九十': 90, '一百': 100
    }
    
    # 如果是数字，直接返回
    if text.isdigit():
        return int(text)
    
    # 🔧 修复：按照长度从长到短匹配，避免"四十"被误识别为"四"
    # 将字典项按照中文数字长度从长到短排序
    sorted_chinese_nums = sorted(chinese_nums.items(), key=lambda x: len(x[0]), reverse=True)
    
    # 尝试转换中文数字，优先匹配更长的数字
    for chinese, num in sorted_chinese_nums:
        if chinese in text:
            print(f"🔢 匹配到中文数字: '{chinese}' -> {num}")
            return num
    
    # 如果没找到，尝试提取数字
    import re
    numbers = re.findall(r'\d+', text)
    if numbers:
        print(f"🔢 提取到阿拉伯数字: {numbers[0]}")
        return int(numbers[0])
    
    print(f"⚠️ 无法解析数字: {text}")
    return None

def control_volume(volume_text):
    """
    调节音量
    
    Args:
        volume_text: 音量值，可以是数字或中文数字，如"20"、"二十"等
    
    Returns:
        str: 调节结果
    """
    try:
        print(f"🔊 收到音量控制指令: {volume_text}")
        
        # 转换中文数字
        volume_value = _convert_chinese_number(str(volume_text))
        
        if volume_value is None:
            return "抱歉，我无法理解这个音量数值，请说一个0到100之间的数字。"
        
        if not (0 <= volume_value <= 100):
            return "音量数值应该在0到100之间，请重新设置。"
        
        # 调用设置控制函数
        from function_handlers import _send_settings_control_command
        success = _send_settings_control_command("volume", volume_value)
        
        if success:
            return f"好的，正在调节音量到{volume_value}"
        else:
            return "抱歉，音量调节失败，请稍后再试。"
            
    except Exception as e:
        print(f"❌ 音量控制异常: {e}")
        return "抱歉，音量调节遇到了问题，请稍后再试。"

fun_control_volume_desc = {
    "type": "function",
    "function": {
        "name": "control_volume",
        "description": "调节系统音量。当用户说要调节音量、声音大小时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "volume_text": {
                    "type": "string",
                    "description": "音量数值，可以是数字或中文数字，如'20'、'二十'、'50'等，范围0-100"
                }
            },
            "required": ["volume_text"]
        }
    }
}

def control_brightness(brightness_text):
    """
    调节亮度
    
    Args:
        brightness_text: 亮度值，可以是数字或中文数字，如"30"、"三十"等
    
    Returns:
        str: 调节结果
    """
    try:
        print(f"💡 收到亮度控制指令: {brightness_text}")
        
        # 转换中文数字
        brightness_value = _convert_chinese_number(str(brightness_text))
        
        if brightness_value is None:
            return "抱歉，我无法理解这个亮度数值，请说一个0到100之间的数字。"
        
        if not (0 <= brightness_value <= 100):
            return "亮度数值应该在0到100之间，请重新设置。"
        
        # 调用设置控制函数
        from function_handlers import _send_settings_control_command
        success = _send_settings_control_command("brightness", brightness_value)
        
        if success:
            return f"好的，正在调节亮度到{brightness_value}"
        else:
            return "抱歉，亮度调节失败，请稍后再试。"
            
    except Exception as e:
        print(f"❌ 亮度控制异常: {e}")
        return "抱歉，亮度调节遇到了问题，请稍后再试。"

fun_control_brightness_desc = {
    "type": "function",
    "function": {
        "name": "control_brightness",
        "description": "调节系统亮度、灯光。当用户说要调节亮度、灯光、光线、光照时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "brightness_text": {
                    "type": "string",
                    "description": "亮度数值，可以是数字或中文数字，如'30'、'三十'、'80'等，范围0-100"
                }
            },
            "required": ["brightness_text"]
        }
    }
}

def control_desk_height(height_text):
    """
    调节桌子高度
    
    Args:
        height_text: 高度档位，可以是数字或中文数字，如"2"、"二"等
    
    Returns:
        str: 调节结果
    """
    try:
        print(f"📏 收到桌子高度控制指令: {height_text}")
        
        # 转换中文数字
        height_value = _convert_chinese_number(str(height_text))
        
        if height_value is None:
            return "抱歉，我无法理解这个高度档位，请说1到3档之间的数字。"
        
        if not (1 <= height_value <= 3):
            return "桌子高度应该在1到3档之间，请重新设置。"
        
        # 调用设置控制函数
        from function_handlers import _send_settings_control_command
        success = _send_settings_control_command("desk_height", height_value)
        
        if success:
            return f"好的，正在调节桌子高度到{height_value}档"
        else:
            return "抱歉，桌子高度调节失败，请稍后再试。"
            
    except Exception as e:
        print(f"❌ 桌子高度控制异常: {e}")
        return "抱歉，桌子高度调节遇到了问题，请稍后再试。"

fun_control_desk_height_desc = {
    "type": "function",
    "function": {
        "name": "control_desk_height",
        "description": "调节桌子高度。当用户说要调节桌子高度、桌面高低时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "height_text": {
                    "type": "string",
                    "description": "桌子高度档位，可以是数字或中文数字，如'1'、'一'、'2'、'二'、'3'、'三'等，范围1-3档"
                }
            },
            "required": ["height_text"]
        }
    }
}

# 🔧 新增：功能切换工具描述符
def open_homework_correction():
    """
    打开作业批改功能
    
    Returns:
        str: 执行结果
    """
    try:
        print(f"📚 MCP调用：启动作业批改功能...")
        
        # 调用功能处理器
        from function_handlers import get_function_handlers
        handlers = get_function_handlers()
        success = handlers.open_homework_correction()
        
        if success:
            return "好的，作业批改功能已启动，请准备拍摄作业照片。"
        else:
            return "抱歉，作业批改功能启动失败，请稍后再试。"
            
    except Exception as e:
        print(f"❌ 打开作业批改功能异常: {e}")
        return "抱歉，打开作业批改功能时遇到了问题，请稍后再试。"

fun_open_homework_correction_desc = {
    "type": "function",
    "function": {
        "name": "open_homework_correction",
        "description": "打开作业批改功能。当用户说要打开作业批改、启动作业批改、作业批改功能时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def open_homework_qa():
    """
    打开作业问答功能
    
    Returns:
        str: 执行结果
    """
    try:
        print(f"📝 MCP调用：启动作业问答功能...")
        
        # 调用功能处理器
        from function_handlers import get_function_handlers
        handlers = get_function_handlers()
        success = handlers.open_homework_qa()
        
        if success:
            return "好的，作业问答功能已启动，请准备拍摄题目照片。"
        else:
            return "抱歉，作业问答功能启动失败，请稍后再试。"
            
    except Exception as e:
        print(f"❌ 打开作业问答功能异常: {e}")
        return "抱歉，打开作业问答功能时遇到了问题，请稍后再试。"

fun_open_homework_qa_desc = {
    "type": "function",
    "function": {
        "name": "open_homework_qa",
        "description": "打开作业问答功能。当用户说要打开作业问答、启动作业问答、作业问答功能时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def open_system_settings():
    """
    打开系统设置功能
    
    Returns:
        str: 执行结果
    """
    try:
        print(f"⚙️ MCP调用：启动系统设置功能...")
        
        # 调用功能处理器
        from function_handlers import get_function_handlers
        handlers = get_function_handlers()
        success = handlers.open_system_settings()
        
        if success:
            return "好的，系统设置功能已打开，您可以调节音量、亮度等设置。"
        else:
            return "抱歉，系统设置功能启动失败，请稍后再试。"
            
    except Exception as e:
        print(f"❌ 打开系统设置功能异常: {e}")
        return "抱歉，打开系统设置功能时遇到了问题，请稍后再试。"

fun_open_system_settings_desc = {
    "type": "function",
    "function": {
        "name": "open_system_settings",
        "description": "打开系统设置功能。当用户说要打开设置、系统设置、调节设置时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def generate_teaching_plan(topic):
    """
    生成教案
    
    Args:
        topic: 教案主题
        
    Returns:
        str: 执行结果
    """
    try:
        logger.info(f"📚 Function Calling: 生成关于'{topic}'的教案")
        
        # 调用阿里云百炼API生成教案
        from aliyun_bailian_api import generate_teaching_plan_api
        
        teaching_plan_content = generate_teaching_plan_api(topic)
        
        if not teaching_plan_content:
            return f"抱歉，生成关于'{topic}'的教案失败，请稍后再试。"
        
        # 保存教案到数据库
        from teaching_plan_database import save_teaching_plan_to_db
        
        save_success = save_teaching_plan_to_db(teaching_plan_content, topic)
        
        if save_success:
            logger.info(f"✅ 教案生成并保存成功，主题: {topic}")
            return f"好的，已经为您生成关于'{topic}'的教案，请您到web界面查看。"
        else:
            logger.warning(f"⚠️ 教案生成成功但保存失败，主题: {topic}")
            return f"好的，已经为您生成关于'{topic}'的教案，但保存到数据库时遇到了问题，请联系管理员。"
            
    except Exception as e:
        logger.error(f"❌ 生成教案异常: {e}")
        return f"抱歉，生成关于'{topic}'的教案时遇到了问题，请稍后再试。"

fun_generate_teaching_plan_desc = {
    "type": "function",
    "function": {
        "name": "generate_teaching_plan",
        "description": "调用阿里云百炼平台生成教案。当用户说要生成教案、帮我生成教案、制作教案等时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "教案的主题，如新能源、红楼梦、力学等"
                }
            },
            "required": ["topic"]
        }
    }
}

def summarize_ppt_content():
    """
    总结PPT内容
    
    Returns:
        str: 执行结果
    """
    try:
        logger.info(f"📊 Function Calling: 开始总结今天老师讲的PPT内容")
        
        # 从数据库读取最新的PPT内容
        from ppt_database import get_latest_ppt_content
        
        ppt_content = get_latest_ppt_content()
        
        if not ppt_content:
            return "抱歉，没有找到今天老师讲的PPT内容，可能还没有上传或数据库中没有记录。"
        
        # 使用AI对PPT内容进行总结
        from openai import OpenAI
        import os
        
        # 获取AI客户端配置
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        base_url = os.environ.get("DASHSCOPE_BASE_URL")
        model_name = os.environ.get("DASHSCOPE_MODEL", "qwen-turbo")
        
        if not api_key or not base_url:
            logger.error("❌ 缺少AI API配置")
            return "抱歉，AI服务配置不完整，无法进行内容总结。"
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 构建总结提示词
        summary_prompt = f"""
请帮我总结一下今天老师讲的PPT内容，要求：
1. 用简洁明了的语言概括主要知识点
2. 突出重点和难点
3. 适合学生理解的表达方式
4. 总结不超过100字

PPT内容如下：
{ppt_content}
"""
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个优秀的教学助手，擅长将复杂的内容总结成简单易懂的形式。"},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=30
        )
        
        summary = response.choices[0].message.content
        
        logger.info(f"✅ PPT内容总结完成，长度: {len(summary)} 字符")
        return f"好的！我来为你总结一下今天老师讲的内容：\n\n{summary}"
        
    except Exception as e:
        logger.error(f"❌ PPT内容总结异常: {e}")
        return "抱歉，总结PPT内容时遇到了问题，请稍后再试。"

fun_summarize_ppt_content_desc = {
    "type": "function",
    "function": {
        "name": "summarize_ppt_content",
        "description": "总结今天老师讲的PPT内容。当用户说要总结PPT、今天老师讲了什么、帮我总结一下今天的课程内容等时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

# 修改默认工具，包含更多常用功能（已移除拍照搜题功能）
tools=[
    fun_currentDatetime_desc,  # 添加时间查询工具
    tool_addReminder_des,      # 添加定时提醒功能
    tool_removeReminder_des,   # 添加移除提醒功能
    fun_playmusic_desc,        # 添加音乐播放工具
    fun_stopplay_desc,         # 添加停止播放工具
    fun_playTTSAudio_desc,     # 添加TTS音频播放工具
    # fun_solve_problem_desc,  # 已移除拍照搜题功能
    fun_clear_cache_desc,      # 添加清理缓存功能
    fun_control_volume_desc,   # 🔧 新增：音量控制
    fun_control_brightness_desc, # 🔧 新增：亮度控制  
    fun_control_desk_height_desc, # 🔧 新增：桌子高度控制
    # 🔧 新增：功能切换工具
    fun_open_homework_correction_desc, # 打开作业批改功能
    fun_open_homework_qa_desc,         # 打开作业问答功能
    fun_open_system_settings_desc,     # 打开系统设置功能
    fun_generate_teaching_plan_desc,   # 生成教案功能
    fun_summarize_ppt_content_desc,    # PPT内容总结功能
    tool_dismissAssistant_des, # 添加退下功能
    tool_setLLMVersion_des,
    # tool_switchRole_des,      # 注释掉switchRole，避免正常聊天时的不必要调用
    tool_setQuit_des
]