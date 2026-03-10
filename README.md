# 智能学习助手

一个基于PyQt5和MQTT协议的智能学习助手应用程序，支持学校和家庭两种使用环境。
具体显示视频可以参考如下链接：

[演示视频](https://www.bilibili.com/video/BV122bHzaEtY/?spm_id_from=333.1387.0.0&vd_source=9119a12881bb469e8838fcc25f9e9b31)


## 功能特性

### 现代化UI设计
- **卡片式界面**：采用现代化的卡片式设计风格
- **横滑导航**：每个功能以独立卡片展示，支持左右滑动浏览
- **白色通知卡片**：简洁美观的通知样式
- **响应式指示器**：实时显示当前选择的功能

### 环境选择
- **学校环境**：提供设置、作业批改、视频连接、语音助手功能
- **家庭环境**：提供设置、作业批改、视频连接、语音助手、作业问答、通知功能

### 主要功能
1. **MQTT远程控制**：通过MQTT协议接收控制指令
2. **视频会议**：自动加入MiroTalk视频会议
3. **智能通知**：支持通知消息和视频邀请的弹窗提醒
4. **环境适配**：根据选择的环境自动调整可用功能
5. **横滑体验**：移动设备般的滑动操作体验

## MQTT控制指令

| 指令 | 功能 |
|------|------|
| 6-0-1 | 确认 |
| 6-0-2 | 返回 |
| 6-0-3 | 下一页/下一个/右边 |
| 6-0-4 | 上一页/上一个/左边 |
| 6-0-5 | 上滑 |
| 6-0-6 | 下滑 |

## 通知消息格式

### 普通通知 (topic: nf)
```json
{
    "type": "notification",
    "from": "sender",
    "to": "receiver",
    "message": "通知内容",
    "schedule_time": "立即发送",
    "timestamp": "2025-06-30 01:40:10"
}
```

### 视频邀请 (topic: room)
```json
{
    "type": "teacher_connect_request",
    "from": "teacher",
    "to": "student",
    "room_id": "45698PoorChair",
    "mirotalk_url": "https://p2p.mirotalk.com/join?room=45698PoorChair&name=teacher&video=0&audio=0&notify=0",
    "timestamp": "2025-07-02 14:01:00"
}
```

## 安装和运行

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行应用
```bash
python main.py
```

### 测试功能
使用提供的测试脚本来测试MQTT功能：
```bash
python test_mqtt.py
```
测试脚本可以：
- 发送控制指令测试界面导航
- 发送通知消息测试通知显示
- 发送视频邀请测试会议功能
- 发送房间关闭指令测试会议结束

## 配置说明

所有配置都在 `config.py` 文件中，您可以根据需要调整：

- **窗口大小**：修改 `WINDOW_CONFIG` 中的 width 和 height
- **通知窗口**：修改 `NOTIFICATION_CONFIG` 中的大小和显示时长
- **MQTT设置**：修改 `MQTT_CONFIG` 中的服务器地址和端口

## 项目结构

```
pyqt5/
├── main.py              # 主应用程序
├── config.py            # 配置文件
├── mqtt_handler.py      # MQTT处理模块
├── video_handler.py     # 视频会议处理模块
├── ui_components.py     # UI组件模块
├── requirements.txt     # 依赖包列表
└── img/                 # 图标资源
    ├── settings.png     # 设置图标
    ├── mettings.png     # 视频连接图标
    ├── note.png         # 通知图标
    ├── voice.png        # 语音助手图标
    ├── answer.png       # 作业问答图标
    └── pigai.png        # 作业批改图标
```

## 使用说明

1. **启动应用**：运行 `python main.py`
2. **选择环境**：使用左右键（或MQTT指令6-0-4/6-0-3）选择学校或家庭环境
3. **确认选择**：按回车键（或MQTT指令6-0-1）确认选择
4. **浏览功能**：在主界面使用左右键（或MQTT指令6-0-4/6-0-3）横滑浏览功能卡片
5. **选择功能**：按回车键（或MQTT指令6-0-1）进入当前显示的功能
6. **返回上级**：按ESC键（或MQTT指令6-0-2）返回环境选择界面

### 界面说明
- **环境选择界面**：显示学校和家庭两个选项，带有图标的卡片式设计
- **功能浏览界面**：每次只显示一个功能的大图标，底部有指示器显示当前位置
- **通知显示**：右上角滑入的白色卡片，自动10秒后消失

## 注意事项

- 确保MQTT服务器可以正常连接
- 系统需要安装Firefox或Chrome浏览器用于视频会议
- Windows系统可能需要管理员权限来关闭浏览器进程

## 开发环境

- Python 3.7+
- PyQt5 5.15+
- paho-mqtt 1.6+
- psutil 5.9+ 