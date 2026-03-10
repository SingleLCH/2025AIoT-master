# 设置页面功能说明

## 概述
设置页面是家教机系统的二级页面，用于调节三个物理量：音量、亮度和桌子高度。页面支持通过手势识别传感器的MQTT协议接收控制指令，并向ESP32发送控制硬件的指令。

## 功能特性

### 1. 音量控制
- **类型**: 无极调节（0-100）
- **初始值**: 50
- **图标**: `img/volume.png`
- **显示**: 实时显示音量百分比和进度条
- **调节增量**: 10（可在config.py中配置）

### 2. 亮度控制
- **类型**: 无极调节（0-100）
- **初始值**: 50
- **图标**: `img/light.png`
- **显示**: 实时显示亮度百分比和进度条
- **调节增量**: 10（可在config.py中配置）

### 3. 桌子高度控制
- **类型**: 三档调节（1档、2档、3档）
- **初始值**: 2档（中间）
- **图标**: `img/height.png`
- **显示**: 实时显示档位和档位选择按钮
- **调节增量**: 1档（可在config.py中配置）

## 手势识别控制

### 两种工作模式

#### 1. 常规模式（默认）
- **功能**: 选择变量和粗调数值
- **UI状态**: 选中变量显示绿色边框
- **模式指示**: 右上角显示"常规模式"

#### 2. 连续调节模式
- **功能**: 实时精确调节选中变量
- **UI状态**: 选中变量显示绿色背景
- **模式指示**: 右上角显示"连续调节模式"（绿色背景）

### 手势指令说明

#### 接收指令（来自gesture主题）

##### 常规模式指令
- `6-0-1`: 确认 - 进入连续调节模式
- `6-0-2`: 返回 - 切换回功能选择界面
- `6-0-3`: 右滑 - 增加DELTA
- `6-0-4`: 左滑 - 减少DELTA
- `6-0-5`: 上滑 - 选中上一个变量
- `6-0-6`: 下滑 - 选中下一个变量

##### 连续调节模式指令
- `6-0-8`: 退出连续调节模式
- `6-1-X`: 设置当前变量为X（0≤X≤100）

#### 发送指令

##### 手势模式切换（发送到gesture_switch主题）
- `6-0-7`: 进入连续滑动模式

##### ESP32硬件控制（发送到esp32/s2/control主题）
- `4-0-X`: 音量设置为X（0≤X≤100）
- `7-0-X`: 亮度设置为X（0≤X≤100）
- `3-0-X`: 桌子高度设置为X（X∈{1,2,3}）

### 桌子高度区间映射
连续调节模式下，0-100的数值按区间映射到桌子高度档位：
- 0-33: 1档（最低）
- 33-66: 2档（中间）
- 66-100: 3档（最高）

## 操作流程

### 基本操作流程
1. **进入设置页面**: 默认进入常规模式，音量被选中（绿色边框）
2. **选择变量**: 使用上滑(6-0-5)和下滑(6-0-6)切换选中的变量
3. **粗调数值**: 使用右滑(6-0-3)和左滑(6-0-4)按增量调节数值
4. **精确调节**: 确认(6-0-1)进入连续调节模式
5. **实时调节**: 在连续调节模式下，手势传感器发送6-1-X指令实时调节
6. **退出调节**: 手势传感器发送6-0-8指令退出连续调节模式
7. **返回上级**: 在常规模式下，返回(6-0-2)回到功能选择界面

### 状态转换图
```
常规模式 ---(确认)---> 连续调节模式
    ^                        |
    |                        |
    +------(6-0-8)----------+
```

## 界面布局

### 顶部区域
- 左侧：页面标题"设置"
- 右侧：模式状态指示器

### 控制区域
每个控制项包含：
- 图标（32x32像素）
- 名称标签
- 当前数值显示
- 控制组件（滑块或按钮）

### 底部区域
- 操作提示文字（根据当前模式动态更新）

### 样式设计
- 背景色：#f8f9fa
- 控制项背景：白色，圆角10px
- 选中边框：绿色(#28a745)，3px
- 连续调节背景：浅绿色(#d4edda)
- 主色调：#007bff（蓝色）
- 字体：Microsoft YaHei

## 配置参数

### config.py中的相关配置

#### MQTT配置
```python
MQTT_CONFIG = {
    'control_topic': 'gesture',  # 程序控制主题（程序接收，与手势主题统一）
    'hardware_control_topic': 'esp32/s2/control',  # 硬件控制主题（程序发送，不订阅）
    'gesture_topic': 'gesture',  # 手势识别传感器主题
    'gesture_switch_topic': 'gesture_switch',  # 手势模式切换主题
    # ...
}
```

#### 手势识别配置
```python
GESTURE_CONFIG = {
    'delta_volume': 10,      # 音量调节增量
    'delta_brightness': 10,  # 亮度调节增量
    'delta_desk_height': 1,  # 桌子高度调节增量
    
    # 桌子高度区间配置
    'desk_height_ranges': {
        1: (0, 33),    # 1档：0-33
        2: (33, 66),   # 2档：33-66
        3: (66, 100)   # 3档：66-100
    }
}
```

## 文件结构

```
settings_page.py          # 设置页面主要实现
mqtt_handler.py           # MQTT处理器（支持手势识别）
main.py                   # 主程序（集成手势控制）
config.py                 # 配置文件（包含手势配置）
SETTINGS_PAGE_README.md   # 本文档
img/
  ├── volume.png          # 音量图标
  ├── light.png           # 亮度图标
  └── height.png          # 桌子高度图标
```

## 使用方法

### 1. 在主程序中使用
```python
from settings_page import SettingsPage

# 创建设置页面
settings_page = SettingsPage()
settings_page.back_requested.connect(self.on_settings_back)
settings_page.send_gesture_switch_command.connect(self.mqtt_handler.send_gesture_switch_command)
settings_page.send_esp32_control_command.connect(self.mqtt_handler.send_esp32_control_command)

# 处理手势指令
settings_page.handle_gesture_command("6-0-5")  # 选择上一个变量
```

### 2. 测试手势控制
可以通过MQTT客户端向`gesture`主题发送测试指令：
```bash
# 选择下一个变量
mosquitto_pub -h 117.72.8.255 -t gesture -m "6-0-6"

# 增加当前变量
mosquitto_pub -h 117.72.8.255 -t gesture -m "6-0-3"

# 进入连续调节模式
mosquitto_pub -h 117.72.8.255 -t gesture -m "6-0-1"

# 设置当前变量为75
mosquitto_pub -h 117.72.8.255 -t gesture -m "6-1-75"
```

## 技术实现

### 主要类和方法

#### SettingsPage类
- `handle_gesture_command()`: 处理手势指令
- `update_selection_ui()`: 更新选择状态的UI显示
- `select_previous_variable()`: 选择上一个变量
- `select_next_variable()`: 选择下一个变量
- `adjust_current_variable()`: 调节当前选中的变量
- `enter_continuous_mode()`: 进入连续调节模式
- `exit_continuous_mode()`: 退出连续调节模式
- `set_current_variable_value()`: 设置当前变量的值

#### 信号连接
- `send_gesture_switch_command`: 发送手势模式切换指令
- `send_esp32_control_command`: 发送ESP32控制指令
- `back_requested`: 返回按钮点击信号

### 状态管理
- `current_mode`: 当前模式（'normal'/'continuous'）
- `selected_variable`: 当前选中的变量索引
- `variables`: 变量列表['volume', 'brightness', 'desk_height']

### 数据验证
- 音量和亮度：自动限制在0-100范围内
- 桌子高度：自动限制在1-3范围内
- 手势指令：格式验证和错误处理

## MQTT主题设计

为了避免指令循环和明确职责分工，系统采用了分离的MQTT主题设计：

### 接收主题（程序订阅）
- `gesture`: 手势识别指令和程序控制指令（统一主题）
- `nf`, `room`, `roomclose`: 通知相关主题

### 发送主题（程序发布）
- `esp32/s2/control`: 硬件控制指令（音量、亮度、桌子高度）
- `gesture_switch`: 手势模式切换指令
- `sa`: 语音助手指令

**重要**：程序不会订阅`esp32/s2/control`主题，避免接收到自己发送的硬件控制指令。

## 注意事项

1. **MQTT连接**: 确保MQTT服务器(117.72.8.255)连接正常
2. **主题分离**: 程序不订阅`esp32/s2/control`，避免指令循环
3. **图标文件**: 确保 `img/` 目录下有相应的图标文件
4. **手势传感器**: 需要正确配置手势识别传感器的MQTT主题
5. **ESP32设备**: 确保ESP32设备能正常接收控制指令
6. **字体支持**: 建议使用支持中文的字体
7. **响应式设计**: 界面适配1024x768分辨率

## 故障排除

### 常见问题

1. **手势指令无响应**
   - 检查MQTT服务器连接
   - 确认gesture主题订阅正常
   - 查看日志输出

2. **模式切换失败**
   - 检查手势传感器是否正确发送6-0-8指令
   - 确认模式状态显示是否正确

3. **ESP32控制无效**
   - 检查esp32/s2/control主题是否正确
   - 确认ESP32设备在线状态

### 调试方法

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **监控MQTT消息**
   ```bash
   # 监控手势指令
   mosquitto_sub -h 117.72.8.255 -t gesture
   
   # 监控手势模式切换
   mosquitto_sub -h 117.72.8.255 -t gesture_switch
   
   # 监控发送给硬件的控制指令
   mosquitto_sub -h 117.72.8.255 -t esp32/s2/control
   
   # 监控程序接收的控制指令（如果需要）
   mosquitto_sub -h 117.72.8.255 -t app/control
   ```

## 扩展功能

可以考虑添加以下功能：
- 更多物理量的控制（温度、湿度等）
- 自定义手势配置
- 语音反馈集成
- 设置项的保存和恢复
- 场景模式（学习、休息等）

## 维护和更新

### 添加新的控制变量
1. 在`variables`列表中添加新变量
2. 在`control_widgets`中添加对应的UI组件
3. 在`adjust_current_variable()`中添加调节逻辑
4. 在`set_current_variable_value()`中添加设置逻辑
5. 更新config.py中的相关配置

### 修改手势指令
1. 更新`config.py`中的`GESTURE_COMMANDS`
2. 修改`handle_gesture_command()`方法
3. 更新文档说明

### 调整UI样式
1. 修改`update_selection_ui()`方法中的CSS样式
2. 调整颜色、边框、字体等视觉效果
3. 确保在不同状态下的视觉一致性 