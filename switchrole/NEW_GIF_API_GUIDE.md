# 新GIF API架构使用指南

## 🎯 设计思路

按照用户需求实现的全新架构：
- **GIF独立运行**: GIF播放器作为独立服务持续运行
- **API接口控制**: 通过简单的API函数控制GIF状态切换
- **解耦设计**: 语音助手和GIF播放器完全分离，通过API通信

## 📁 文件结构

```
switchrole/
├── gif_api_server.py     # 独立GIF播放器服务
├── gif_api_client.py     # GIF API客户端（供语音助手调用）
├── xiaoxin2_zh.py        # 语音助手主程序（已集成API调用）
├── start_with_new_gif.py # 测试启动脚本
└── gif/                  # GIF文件目录
    ├── daiji.gif         # 待机
    ├── lingting.gif      # 聆听
    ├── mimang.gif        # 思考
    ├── kaixin.gif        # 开心
    ├── shengqi.gif       # 生气
    └── ...
```

## 🚀 使用方法

### 1. 只测试GIF API服务
```bash
python start_with_new_gif.py gif
```
- 启动800x480独立GIF窗口
- 自动测试状态切换
- 验证GIF播放是否正常

### 2. 测试语音助手+GIF集成
```bash
python start_with_new_gif.py voice
```
- 启动完整的语音助手系统
- GIF会根据对话状态自动切换
- 支持情感分析自动表情切换

### 3. 交互式测试
```bash
python start_with_new_gif.py test
```
- 手动输入命令测试GIF切换
- 可以测试文本情感分析
- 实时调试API功能

### 4. 直接运行语音助手
```bash
python xiaoxin2_zh.py
```
- 会自动启动GIF API服务
- 语音对话时自动切换GIF状态

## 🎬 API接口说明

### 状态设置
```python
from gif_api_client import gif_set_state

gif_set_state("idle")       # 待机
gif_set_state("listening")  # 聆听  
gif_set_state("thinking")   # 思考
gif_set_state("speaking")   # 说话
gif_set_state("sleeping")   # 休眠
```

### 情感设置
```python
from gif_api_client import gif_set_emotion

gif_set_emotion("happy")      # 开心
gif_set_emotion("angry")      # 生气
gif_set_emotion("sad")        # 难过
gif_set_emotion("shy")        # 害羞
gif_set_emotion("surprised")  # 惊讶
gif_set_emotion("confused")   # 困惑
gif_set_emotion("bored")      # 无聊
```

### 智能情感分析
```python
from gif_api_client import gif_set_emotion_from_text

gif_set_emotion_from_text("我今天很开心！")  # 自动检测为happy
gif_set_emotion_from_text("这让我很生气")    # 自动检测为angry
```

## 🔄 触发时机

语音助手会在以下时机自动调用API：

1. **程序启动** → `gif_set_state("idle")` (待机)
2. **检测到唤醒词** → `gif_set_state("listening")` (聆听)
3. **用户开始说话** → `gif_set_state("listening")` (聆听)
4. **AI开始处理** → `gif_set_state("thinking")` (思考)
5. **AI生成回复** → `gif_set_emotion_from_text(response)` (情感分析)
6. **对话结束** → `gif_set_state("idle")` (延迟3秒后待机)

## 🎭 情感分析规则

系统会根据AI回复文本中的关键词自动分析情感：

- **开心**: 开心、高兴、快乐、愉快、兴奋、哈哈、太好了、棒、赞、笑、乐
- **生气**: 生气、愤怒、气愤、恼火、暴躁、讨厌、可恶、火大、怒、恨
- **难过**: 难过、痛苦、难受、不舒服、苦恼、郁闷、沮丧、失落、伤心、心痛、悲伤
- **害羞**: 害羞、脸红、不好意思、羞涩、腼腆、羞怯、羞羞、羞人
- **惊讶**: 惊讶、意外、没想到、调皮、淘气、嘻嘻、嘿嘿
- **困惑**: 迷茫、困惑、不知道、搞不懂、茫然、疑惑、不明白、懵
- **无聊**: 无聊、闲着、没事做、乏味、单调、枯燥、无趣

## 🐛 故障排除

### 问题1: GIF窗口不显示
```bash
# 测试基础GIF服务
python gif_api_server.py --test
```

### 问题2: API调用无响应
```bash
# 测试API客户端
python gif_api_client.py --test
```

### 问题3: 语法错误已修复
- 已修复`xiaoxin2_zh.py`中的`global`声明问题
- 使用新的API架构替换了复杂的集成模块

### 问题4: 窗口大小
- 固定为800x480像素（按用户要求）
- 窗口自动居中显示
- 白色背景，清晰边框

## 💡 优势特点

1. **独立运行**: GIF播放器独立于语音助手，崩溃互不影响
2. **简单API**: 只需3个函数就能控制所有GIF状态
3. **智能分析**: 自动从文本分析情感，无需手动映射
4. **解耦设计**: 修改GIF逻辑不需要重启语音助手
5. **易于调试**: 可以单独测试GIF功能
6. **资源优化**: 减少内存占用和进程冲突

## 🎉 总结

新架构完全按照用户思路实现：
- ✅ GIF一直播放，独立运行
- ✅ 预留简单的API接口
- ✅ 语音控制发送信息给GIF
- ✅ GIF接收信息后自动切换
- ✅ 修复了语法错误
- ✅ 实现了800x480窗口大小

现在可以：
1. 先测试`python start_with_new_gif.py gif`确认GIF窗口显示正常
2. 再测试`python start_with_new_gif.py voice`验证语音集成
3. 最后直接运行`python xiaoxin2_zh.py`享受完整体验！ 