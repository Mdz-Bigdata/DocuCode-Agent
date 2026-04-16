<!---
Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

中文 ｜ [English](README.md)
<br>

<p align="center">
          💜 <a href="https://chat.qwen.ai/"><b>Qwen Chat</b></a>&nbsp&nbsp | &nbsp&nbsp🤗 <a href="https://huggingface.co/Qwen">Hugging Face</a>&nbsp&nbsp | &nbsp&nbsp🤖 <a href="https://modelscope.cn/organization/qwen">ModelScope</a>&nbsp&nbsp | &nbsp&nbsp 📑 <a href="https://qwenlm.github.io/">Blog</a> &nbsp&nbsp ｜ &nbsp&nbsp📖 <a href="https://qwenlm.github.io/Qwen-Agent/en/">Documentation</a>

<br>
📊 <a href="https://qwenlm.github.io/Qwen-Agent/en/benchmarks/deepplanning/">Benchmark</a>&nbsp&nbsp | &nbsp&nbsp💬 <a href="https://github.com/QwenLM/Qwen/blob/main/assets/wechat.png">WeChat (微信)</a>&nbsp&nbsp | &nbsp&nbsp🫨 <a href="https://discord.gg/CV4E9rpNSD">Discord</a>&nbsp&nbsp
</p>

# DocuCode-Agent

DocuCode-Agent 是一个基于 Qwen-Agent 构建的综合 LLM 应用开发框架。它增强了通义千问模型的指令遵循、工具使用、规划和记忆能力，并特别关注文档处理和代码相关任务。

本项目提供了 Ultimate 终极版本，包含完整的 Web UI、RAG（检索增强生成）系统，以及用于文档问答、代码辅助等各种专用智能体。

## 功能特性

- **多智能体系统**：支持协作式智能体，具备自动路由能力
- **高级 RAG 引擎**：混合检索（向量 + BM25）、查询重写、HyDE、ColBERT、CrossEncoder 和知识图谱验证
- **文档处理**：支持 PDF、Word、Excel、PowerPoint 和各种文本格式
- **代码解释器**：基于 Docker 的安全代码执行环境
- **MCP（模型上下文协议）**：与 MCP 服务器集成以扩展工具能力
- **Web UI**：完整的 Ultimate 网页界面，包含多个功能模块
- **自定义工具**：轻松集成自定义工具和技能

## 项目结构

```
DocuCode-Agent/
├── docucode_agent/          # 核心框架库
│   ├── agents/              # 各种智能体实现
│   │   ├── doc_qa/         # 文档问答智能体
│   │   ├── keygen_strategies/  # 查询生成策略
│   │   ├── writing/        # 写作辅助智能体
│   │   └── ...
│   ├── gui/                 # 基于 Gradio 的 GUI 组件
│   ├── llm/                 # LLM 集成（DashScope、OpenAI 兼容）
│   ├── memory/              # 记忆管理
│   ├── tools/               # 内置工具
│   │   ├── search_tools/   # 搜索工具
│   │   ├── doc_parser.py   # 文档解析器
│   │   └── ...
│   └── utils/               # 工具函数
├── ultimate/                 # Ultimate 版本 Web 应用
│   ├── static/              # 前端静态文件
│   ├── uploads/             # 上传文件存储
│   ├── backend.py           # FastAPI 后端
│   └── start.py             # 启动脚本
├── .env                      # 环境变量
├── .env.example             # 环境变量示例
├── setup.py                 # 包设置
└── LICENSE                  # Apache 2.0 许可证
```

## 安装

### 前置要求

- Python 3.10+
- Docker（用于代码解释器）
- Node.js 和 uv（用于 MCP）

### 从源码安装

```bash
git clone https://github.com/Mdz-Bigdata/DocuCode-Agent.git
cd DocuCode-Agent
pip install -e ".[gui,rag,code_interpreter,mcp]"
```

最小化安装（不含可选依赖）：

```bash
pip install -e .
```

### 可选依赖

- `[gui]` - 基于 Gradio 的 GUI 支持
- `[rag]` - RAG（检索增强生成）支持
- `[code_interpreter]` - 代码解释器支持
- `[mcp]` - MCP（模型上下文协议）支持

## 快速开始

### 1. 配置 API Key

复制 `.env.example` 为 `.env` 并设置您的 API Key：

```bash
cp .env.example .env
# 编辑 .env 并设置 DASHSCOPE_API_KEY
```

或通过环境变量设置：

```bash
export DASHSCOPE_API_KEY="your-api-key"
```

### 2. 启动 Ultimate Web UI

```bash
cd ultimate
python start.py
```

然后打开浏览器访问 `http://localhost:8000`。

### 3. 基本使用示例

```python
from docucode_agent.agents import Assistant
from docucode_agent.utils.output_beautify import typewriter_print

# 配置 LLM
llm_cfg = {
    'model': 'qwen-max-latest',
    'model_type': 'qwen_dashscope',
}

# 创建智能体
bot = Assistant(
    llm=llm_cfg,
    system_message='你是一个有用的助手。',
    function_list=['web_search', 'code_interpreter']
)

# 与智能体对话
messages = []
while True:
    query = input('\n用户输入: ')
    messages.append({'role': 'user', 'content': query})
    response = []
    response_plain_text = ''
    print('机器人回复:')
    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(response, response_plain_text)
    messages.extend(response)
```

## Ultimate 版本功能

Ultimate 版本提供了完整的网页界面，包含以下模块：

### 📚 RAG 模块
- 文档上传和管理
- 混合搜索（向量 + BM25）
- ColBERT 和 CrossEncoder 高级检索
- 知识图谱验证

### 💻 代码助手
- 代码生成和解释
- 代码解释器执行
- 代码审查和优化建议

### 🤖 客服机器人
- 多轮对话
- 上下文管理
- 知识库集成

### 🔧 MCP 工具
- 与 MCP 服务器集成
- 文件系统访问
- 数据库操作
- 自定义工具注册

### ⚙️ 设置
- API 配置
- 模型选择
- 系统偏好设置

## 高级 RAG 引擎

DocuCode-Agent 具有先进的 RAG 管道，包括：

- **查询重写**：生成多个查询变体以提高检索效果
- **HyDE（假设文档嵌入）**：生成假设性答案以改善检索
- **混合检索**：结合向量搜索和 BM25 关键词搜索
- **ColBERT 风格检索**：令牌级相似度匹配
- **CrossEncoder 重排序**：细粒度相关性评分
- **知识图谱验证**：基于实体的置信度评分
- **上下文压缩**：智能上下文选择和压缩

## 工具

### 内置工具

- `web_search` - 网页搜索功能
- `code_interpreter` - 沙箱中的 Python 代码执行
- `doc_parser` - 文档解析（PDF、Word 等）
- `image_gen` - 图像生成
- `amap_weather` - 天气信息
- 等等...

### 自定义工具

您可以轻松添加自定义工具：

```python
from docucode_agent.tools.base import BaseTool, register_tool
import json5

@register_tool('my_custom_tool')
class MyCustomTool(BaseTool):
    description = '该工具的功能描述。'
    parameters = [{
        'name': 'param1',
        'type': 'string',
        'description': '参数描述',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        args = json5.loads(params)
        # 您的工具逻辑在此
        return json5.dumps({'result': 'success'})
```

## 常见问题

### 如何使用代码解释器？

代码解释器需要安装并运行 Docker。首次运行将构建 Docker 镜像，根据您的网络情况可能需要一些时间。

### 如何部署自己的模型服务？

您可以使用 vLLM 或 Ollama 部署 Qwen 模型以提供 OpenAI 兼容的 API 服务。详情请参阅 Qwen 文档。

### 如何处理超长文档？

DocuCode-Agent 为长文档提供了优化的 RAG 解决方案，能够高效处理 100 万+ 令牌的上下文。

## 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 致谢

- 基于阿里巴巴集团的 [Qwen-Agent](https://github.com/QwenLM/Qwen-Agent) 构建
- 使用阿里云 DashScope 的 Qwen 模型

## 贡献

欢迎贡献！请随时提交问题、功能请求或拉取请求。

## 免责声明

基于 Docker 容器的代码解释器仅挂载指定的工作目录并实现基本的沙箱隔离，但在生产环境中仍应谨慎使用。
