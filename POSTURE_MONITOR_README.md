# 智能姿势检测系统

## 概述
这是一个基于PyQt5和YOLOv11的智能姿势检测系统，能够实时监控用户的坐姿，检测低头等不良姿势，并及时提醒用户调整。

## 功能特点
- 🎯 **实时姿势检测**: 基于YOLOv11姿态检测模型，精确识别人体关键点
- 📸 **智能拍照**: 定时自动拍照，无需手动操作
- ⚠️ **姿势警告**: 检测到连续不良姿势时自动提醒
- 📊 **统计分析**: 提供详细的姿势统计数据和历史记录
- 🎨 **友好界面**: 直观的图形用户界面，操作简单
- ⚙️ **灵活配置**: 支持自定义检测间隔、警告阈值等参数

## 系统要求
- Python 3.7+
- 摄像头设备
- Linux/Windows/macOS

## 安装依赖
```bash
# 安装基础依赖
pip install opencv-python PyQt5 Pillow numpy

# 安装AI模型库
pip install ultralytics

# Linux系统安装中文字体（可选）
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei
```

## 文件结构
```
pyqt5/
├── start_posture_monitor.py    # 启动脚本
├── posture_monitor_ui.py       # 主界面
├── pose_detection_thread.py    # 检测线程
├── pose_detector.py           # 姿势检测器
├── camera_handler.py          # 摄像头处理器
├── config.py                  # 配置文件
└── install_chinese_fonts.py   # 字体安装脚本（Linux）
```

## 快速开始

### 1. 启动系统
```bash
cd /home/fibo/code/VoiceAssistant-main/pyqt5
python start_posture_monitor.py
```

### 2. 界面操作
- **开始检测**: 点击"🎯 开始检测"按钮
- **暂停/继续**: 点击"⏸️ 暂停"按钮
- **停止检测**: 点击"⏹️ 停止检测"按钮
- **清除历史**: 点击"🗑️ 清除历史"按钮

### 3. 设置调整
- **检测间隔**: 设置拍照检测的时间间隔（1-60秒）
- **警告阈值**: 设置连续检测到不良姿势多少次后发出警告
- **保存检测图片**: 是否保存每次检测的结果图片
- **姿势警告提醒**: 是否启用不良姿势警告功能

## 配置说明

### 主要配置项（config.py）
```python
# 姿势检测配置
POSE_DETECTION_CONFIG = {
    'detection_interval': 5.0,  # 检测间隔（秒）
    'consecutive_bad_posture_threshold': 3,  # 警告阈值（次）
    'save_detection_images': True,  # 保存检测图片
    'alert_on_bad_posture': True,  # 启用姿势警告
}

# 摄像头配置
CAMERA_CONFIG = {
    'face_camera_name': "UNIQUESKY_CAR_CAMERA: Integrate",
    'photo_camera_name': "DECXIN: DECXIN",
    'preview_width': 640,
    'preview_height': 480,
}
```

## 姿势检测原理

### 检测方法
系统通过分析人体关键点的位置关系来判断姿势：
1. **鼻子位置**: 检测鼻子相对于肩膀连线的位置
2. **低头判断**: 当鼻子低于肩膀连线时判定为低头
3. **严重程度**: 根据偏移距离计算低头严重程度
4. **近视风险**: 分析鼻子到图片底部的距离评估近视风险

### 检测级别
- **正常**: 鼻子高于肩膀连线
- **轻微低头**: 低头程度 < 0.15
- **中度低头**: 0.15 ≤ 低头程度 < 0.3
- **严重低头**: 低头程度 ≥ 0.3

## 故障排除

### 摄像头问题
```bash
# 检查摄像头设备
ls /dev/video*

# 查看摄像头信息
v4l2-ctl --list-devices
```

### 字体显示问题（Linux）
```bash
# 运行字体安装脚本
python install_chinese_fonts.py

# 手动安装中文字体
sudo apt-get install fonts-wqy-microhei
```

### 模型下载问题
如果YOLOv11模型下载失败，可以：
1. 检查网络连接
2. 手动下载模型文件并放置在项目目录
3. 使用代理或镜像源

## 日志文件
系统运行日志保存在 `posture_monitor.log` 文件中，包含：
- 系统启动信息
- 检测结果记录
- 错误信息
- 状态变化

## 性能优化
- 适当调整检测间隔以平衡准确性和性能
- 定期清理历史记录和保存的图片
- 根据设备性能调整图像分辨率

## 注意事项
1. 确保摄像头正常工作且有足够光线
2. 保持面部在摄像头视野范围内
3. 定期更新AI模型以获得更好的检测效果
4. 注意隐私保护，检测图片仅在本地保存

## 技术支持
如遇到问题，请查看：
1. 控制台输出信息
2. 日志文件内容
3. 系统状态显示
4. 确认所有依赖项已正确安装

## 开发信息
- **版本**: 1.0.0
- **开发语言**: Python 3.x
- **UI框架**: PyQt5
- **AI模型**: YOLOv11-pose
- **图像处理**: OpenCV
