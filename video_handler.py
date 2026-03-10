# -*- coding: utf-8 -*-
"""
视频处理模块
"""

import subprocess
import psutil
import logging
import webbrowser
from config import VIDEO_CONFIG

logger = logging.getLogger(__name__)


class VideoHandler:
    """视频会议处理类"""
    
    def __init__(self, mqtt_handler=None):
        self.mqtt_handler = mqtt_handler
        self.current_room_id = None
    
    def join_room(self, room_id):
        """加入视频会议房间"""
        self.current_room_id = room_id
        logger.info(f"准备加入房间: {room_id}")
        
        # 先关闭现有的会议进程
        self.close_mirotalk_processes()
        
        # 构建会议URL
        url = self.build_mirotalk_url(room_id)
        logger.info(f"会议URL: {url}")
        
        # 打开浏览器
        self.open_browser(url)
        
        # 发送SA指令
        if self.mqtt_handler:
            self.mqtt_handler.send_sa_command('5-0-2')
    
    def build_mirotalk_url(self, room_id):
        """构建MiroTalk会议URL"""
        base_url = VIDEO_CONFIG['mirotalk_base_url']
        username = VIDEO_CONFIG['username']
        url = f"{base_url}/join?room={room_id}&name={username}&video=0&audio=1&notify=0"
        return url
    
    def open_browser(self, url):
        """打开浏览器"""
        try:
            # 优先尝试使用Firefox（根据需求）
            browsers = ['firefox', 'google-chrome', 'chromium-browser', 'chromium', 'chrome']
            
            for browser_cmd in browsers:
                try:
                    subprocess.Popen([browser_cmd, url], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    logger.info(f"使用 {browser_cmd} 成功打开会议")
                    return True
                except FileNotFoundError:
                    continue
                except Exception as e:
                    logger.warning(f"使用 {browser_cmd} 打开失败: {e}")
                    continue
            
            # 如果所有浏览器都失败，使用系统默认浏览器
            webbrowser.open(url)
            logger.info("使用系统默认浏览器打开会议")
            return True
            
        except Exception as e:
            logger.error(f"打开浏览器失败: {e}")
            return False
    
    def close_mirotalk_processes(self):
        """关闭所有MiroTalk相关的浏览器进程"""
        logger.info("开始关闭MiroTalk浏览器进程...")
        killed_count = 0
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline') or []
                    # 检查命令行中是否包含MiroTalk域名
                    if any('p2p.mirotalk.com' in arg for arg in cmdline):
                        proc.kill()
                        logger.info(f"已关闭进程 PID={proc.info['pid']}")
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"无法关闭进程 PID={proc.info.get('pid')}: {e}")
                except Exception as e:
                    logger.error(f"处理进程时发生错误: {e}")
                    
        except Exception as e:
            logger.error(f"关闭进程时发生错误: {e}")
        
        logger.info(f"关闭完成，共终止 {killed_count} 个进程")
        return killed_count
    
    def close_current_room(self):
        """关闭当前会议房间"""
        logger.info("关闭当前会议房间")
        self.close_mirotalk_processes()
        self.current_room_id = None
        
        # 发送SA指令
        if self.mqtt_handler:
            self.mqtt_handler.send_sa_command('5-0-1')
    
    def get_current_room_id(self):
        """获取当前房间ID"""
        return self.current_room_id 