#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网易云音乐API模块
提供音乐搜索功能
"""

import requests
import json
import time
import logging

logger = logging.getLogger(__name__)

def search_music(song_name, limit=10):
    """
    搜索音乐
    
    Args:
        song_name (str): 歌曲名称
        limit (int): 搜索结果数量限制
        
    Returns:
        list: 搜索结果列表，每个元素包含歌曲信息
    """
    try:
        print(f"🔍 开始搜索歌曲: {song_name}")
        
        # 网易云音乐搜索API（使用公开接口）
        search_url = "http://music.163.com/api/search/get/web"
        
        params = {
            's': song_name,
            'type': 1,  # 1表示搜索歌曲
            'offset': 0,
            'total': True,
            'limit': limit
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://music.163.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        
        print(f"🌐 发送搜索请求: {search_url}")
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ 搜索请求失败，状态码: {response.status_code}")
            return []
        
        data = response.json()
        
        if 'result' not in data or 'songs' not in data['result']:
            print(f"❌ 搜索结果格式异常: {data}")
            return []
        
        songs = data['result']['songs']
        song_count = data['result'].get('songCount', 0)
        
        print(f"📊 搜索结果: 找到 {song_count} 首歌曲")
        
        # 格式化搜索结果
        formatted_results = []
        for song in songs:
            try:
                song_info = {
                    'id': song['id'],
                    'name': song['name'],
                    'artist': ', '.join([artist['name'] for artist in song['artists']]),
                    'album': song['album']['name'] if song.get('album') else '未知专辑',
                    'duration': song.get('duration', 0),
                    'url': f'http://music.163.com/song/media/outer/url?id={song["id"]}.mp3'
                }
                formatted_results.append(song_info)
                print(f"🎵 找到歌曲: {song_info['name']} - {song_info['artist']}")
            except Exception as e:
                print(f"⚠️ 解析歌曲信息失败: {e}")
                continue
        
        # 返回兼容原格式的结果
        result = {
            'result': {
                'songCount': song_count,
                'songs': [{'id': song['id'], 'name': song['name']} for song in formatted_results]
            }
        }
        
        return result
        
    except requests.exceptions.Timeout:
        print(f"❌ 搜索请求超时")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ 解析JSON响应失败: {e}")
        return []
    except Exception as e:
        print(f"❌ 搜索音乐时发生未知错误: {e}")
        return []

def get_song_url(song_id):
    """
    获取歌曲播放链接
    
    Args:
        song_id (int): 歌曲ID
        
    Returns:
        str: 歌曲播放链接
    """
    try:
        # 网易云音乐外链格式
        url = f'http://music.163.com/song/media/outer/url?id={song_id}.mp3'
        print(f"🔗 生成播放链接: {url}")
        return url
    except Exception as e:
        print(f"❌ 生成播放链接失败: {e}")
        return None

def test_search():
    """测试搜索功能"""
    print("=== 测试网易云音乐搜索 ===")
    
    test_songs = ["晴天", "稻香", "青花瓷"]
    
    for song_name in test_songs:
        print(f"\n🎵 测试搜索: {song_name}")
        results = search_music(song_name, limit=3)
        
        if results and 'result' in results:
            songs = results['result'].get('songs', [])
            print(f"✅ 找到 {len(songs)} 首歌曲")
            for i, song in enumerate(songs[:3]):
                print(f"  {i+1}. {song.get('name', '未知')} (ID: {song.get('id', 'N/A')})")
        else:
            print(f"❌ 搜索失败或无结果")

if __name__ == "__main__":
    test_search()
