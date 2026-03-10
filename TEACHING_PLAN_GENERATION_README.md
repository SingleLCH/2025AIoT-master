# 教案生成功能使用说明

## 功能概述

语音助手现已支持智能教案生成功能。当您说"帮我生成一个关于【主题】的教案"时，语音助手将：

1. 🎯 识别您语音中的主题关键词
2. 🚀 调用阿里云百炼平台生成专业教案
3. 💾 将教案内容保存到远程数据库
4. 📱 返回确认信息，提示您到web界面查看

## 支持的语音命令

以下语音命令都可以触发教案生成功能：

- "帮我生成一个关于**新能源**的教案"
- "请为我制作**红楼梦**的教案"  
- "我需要一个**力学**教案"
- "生成**数学**教案"
- "制作关于**历史**的教案"

**注意**：系统会自动从您的语音中提取主题关键词，如"新能源"、"红楼梦"、"力学"等。

## 配置要求

### 1. 阿里云百炼API配置

在 `xiaoxin.env` 文件中设置：

```bash
# 阿里云百炼API密钥
DASHSCOPE_API_KEY=your_api_key_here
```

### 2. 数据库配置

教案内容将保存到远程MySQL数据库：

- **数据库地址**: poem.e5.luyouxia.net:28298
- **数据库名**: data_info
- **数据表**: jiaoan

**表结构**:
```sql
CREATE TABLE jiaoan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    details TEXT NOT NULL COMMENT '教案内容',
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3. 依赖安装

确保已安装所需依赖：

```bash
pip install pymysql requests
```

## 使用流程

### 1. 启动语音助手

运行语音助手程序：

```bash
python main.py
```

### 2. 语音交互

对语音助手说：

> "帮我生成一个关于**新能源**的教案"

### 3. 系统处理

语音助手将：

1. 🎧 识别您的语音命令
2. 🧠 使用AI模型解析并提取主题"新能源"
3. 📞 调用阿里云百炼平台生成详细教案
4. 💾 将教案保存到数据库表 `jiaoan` 中
5. 🗣️ 语音回复确认信息

### 4. 查看教案

系统会回复：

> "好的！我已经为您生成了关于'新能源'的教案，并保存到了数据库中。请您到web界面查看完整的教案内容。"

## 技术实现

### 1. Function Calling 机制

系统使用 OpenAI 兼容的 Function Calling 标准：

```json
{
  "name": "generate_teaching_plan",
  "description": "调用阿里云百炼平台生成教案",
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
```

### 2. 阿里云百炼API调用

使用阿里云百炼应用 ID: `1c82397ad4cd41f0b06d6b3cefa6c5bc`

API调用流程：
1. 构建请求数据
2. 发送POST请求到百炼平台
3. 解析响应获取教案内容

### 3. 数据库操作

- 使用 PyMySQL 连接数据库
- 自动插入生成时间戳
- 支持线程安全操作

## 文件结构

```
VoiceAssistant-main/pyqt5/
├── switchrole/
│   ├── aliyun_bailian_api.py          # 阿里云百炼API调用模块
│   ├── teaching_plan_database.py      # 数据库操作模块
│   ├── xiaoxin2_skill.py             # Function Calling实现
│   └── xiaoxin2_zh_new.py            # 语音助手主逻辑
├── test_teaching_plan_generation.py   # 功能测试脚本
└── TEACHING_PLAN_GENERATION_README.md # 本说明文档
```

## 测试验证

运行测试脚本验证功能：

```bash
python test_teaching_plan_generation.py
```

测试内容包括：
- ✅ 阿里云API连接测试
- ✅ 数据库连接测试  
- ✅ Function Calling集成测试
- ✅ 语音命令识别模拟

## 故障排除

### 常见问题

**1. API密钥错误**
```
❌ 未找到DASHSCOPE_API_KEY环境变量
```
**解决方案**: 检查 `xiaoxin.env` 文件中的API密钥配置

**2. 数据库连接失败**
```
❌ 数据库连接测试失败
```
**解决方案**: 
- 检查网络连接
- 确认数据库服务器地址和端口
- 设置正确的数据库认证信息

**3. Function Calling未触发**
- 确认语音命令包含"生成"、"教案"等关键词
- 检查 `xiaoxin2_skill.py` 中工具是否正确注册

### 调试方法

1. **查看日志输出**
   系统会输出详细的处理日志，包括：
   - 语音识别结果
   - Function Calling触发情况
   - API调用状态
   - 数据库操作结果

2. **运行测试脚本**
   ```bash
   python test_teaching_plan_generation.py
   ```

3. **手动测试API**
   ```python
   from switchrole.aliyun_bailian_api import generate_teaching_plan_api
   result = generate_teaching_plan_api("测试主题")
   print(result)
   ```

## 扩展功能

### 自定义教案模板

可以在 `aliyun_bailian_api.py` 中修改提示词来定制教案格式：

```python
"prompt": f"请为我生成一个关于'{topic}'的详细教案，包括教学目标、教学重点、教学难点、教学过程和教学总结。"
```

### 添加更多主题识别

在AI模型的Function Calling描述中可以添加更多示例主题。

### 数据库扩展

可以在 `teaching_plan_database.py` 中添加更多字段，如：
- 教案分类
- 难度等级
- 目标年级
- 创建者信息

## 注意事项

1. **API配额**: 阿里云百炼API可能有调用配额限制，请合理使用
2. **网络要求**: 需要稳定的网络连接访问阿里云服务和数据库
3. **数据安全**: 教案内容会保存到远程数据库，请确保数据安全
4. **性能考虑**: 教案生成需要一定时间，请耐心等待

## 更新日志

### v1.0.0 (2025-07-30)
- ✅ 实现基础教案生成功能
- ✅ 集成阿里云百炼平台
- ✅ 添加数据库保存功能
- ✅ 支持Function Calling机制
- ✅ 完善测试和文档

---

**开发团队**: 语音助手开发组  
**最后更新**: 2025-07-30