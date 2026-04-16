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

[中文](README_CN.md) ｜ English


# DocuCode-Agent

DocuCode-Agent is a comprehensive framework for developing LLM applications, built upon the foundation of Qwen-Agent. It enhances the instruction following, tool usage, planning, and memory capabilities of Qwen models, with additional focus on document processing and code-related tasks.

This project provides an Ultimate edition with a complete web UI, RAG (Retrieval-Augmented Generation) system, and various specialized agents for document QA, code assistance, and more.

## Features

- **Multi-Agent System**: Support for collaborative agents with auto-routing capabilities
- **Advanced RAG Engine**: Hybrid retrieval (vector + BM25), query rewriting, HyDE, ColBERT, CrossEncoder, and knowledge graph verification
- **Document Processing**: PDF, Word, Excel, PowerPoint, and various text formats supported
- **Code Interpreter**: Secure code execution environment based on Docker
- **MCP (Model Context Protocol)**: Integration with MCP servers for extended tool capabilities
- **Web UI**: Complete Ultimate web interface with multiple functional modules
- **Custom Tools**: Easy integration of custom tools and skills

## Project Structure

```
DocuCode-Agent/
├── docucode_agent/          # Core framework library
│   ├── agents/              # Various agent implementations
│   │   ├── doc_qa/         # Document QA agents
│   │   ├── keygen_strategies/  # Query generation strategies
│   │   ├── writing/        # Writing assistance agents
│   │   └── ...
│   ├── gui/                 # Gradio-based GUI components
│   ├── llm/                 # LLM integration (DashScope, OpenAI compatible)
│   ├── memory/              # Memory management
│   ├── tools/               # Built-in tools
│   │   ├── search_tools/   # Search tools
│   │   ├── doc_parser.py   # Document parser
│   │   └── ...
│   └── utils/               # Utility functions
├── ultimate/                 # Ultimate edition web application
│   ├── static/              # Frontend static files
│   ├── uploads/             # Uploaded files storage
│   ├── backend.py           # FastAPI backend
│   └── start.py             # Startup script
├── .env                      # Environment variables
├── .env.example             # Environment variables example
├── setup.py                 # Package setup
└── LICENSE                  # Apache 2.0 License
```

## Installation

### Prerequisites

- Python 3.10+
- Docker (for Code Interpreter)
- Node.js and uv (for MCP)

### Install from source

```bash
git clone https://github.com/Mdz-Bigdata/DocuCode-Agent.git
cd DocuCode-Agent
pip install -e ".[gui,rag,code_interpreter,mcp]"
```

For minimal installation (without optional dependencies):

```bash
pip install -e .
```

### Optional Dependencies

- `[gui]` - Gradio-based GUI support
- `[rag]` - RAG (Retrieval-Augmented Generation) support
- `[code_interpreter]` - Code Interpreter support
- `[mcp]` - MCP (Model Context Protocol) support

## Quick Start

### 1. Configure API Key

Copy the `.env.example` to `.env` and set your API key:

```bash
cp .env.example .env
# Edit .env and set DASHSCOPE_API_KEY
```

Or set via environment variable:

```bash
export DASHSCOPE_API_KEY="your-api-key"
```

### 2. Start the Ultimate Web UI

```bash
cd ultimate
python start.py
```

Then open your browser and navigate to `http://localhost:8000`.

### 3. Basic Usage Example

```python
from docucode_agent.agents import Assistant
from docucode_agent.utils.output_beautify import typewriter_print

# Configure LLM
llm_cfg = {
    'model': 'qwen-max-latest',
    'model_type': 'qwen_dashscope',
}

# Create an agent
bot = Assistant(
    llm=llm_cfg,
    system_message='You are a helpful assistant.',
    function_list=['web_search', 'code_interpreter']
)

# Chat with the agent
messages = []
while True:
    query = input('\nuser query: ')
    messages.append({'role': 'user', 'content': query})
    response = []
    response_plain_text = ''
    print('bot response:')
    for response in bot.run(messages=messages):
        response_plain_text = typewriter_print(response, response_plain_text)
    messages.extend(response)
```

## Ultimate Edition Features

The Ultimate edition provides a complete web interface with the following modules:

### 📚 RAG Module
- Document upload and management
- Hybrid search (vector + BM25)
- Advanced retrieval with ColBERT and CrossEncoder
- Knowledge graph verification

### 💻 Code Helper
- Code generation and explanation
- Code interpreter for execution
- Code review and optimization suggestions

### 🤖 Customer Service
- Multi-turn conversation
- Context management
- Knowledge base integration

### 🔧 MCP Tools
- Integration with MCP servers
- File system access
- Database operations
- Custom tool registration

### ⚙️ Settings
- API configuration
- Model selection
- System preferences

## Advanced RAG Engine

DocuCode-Agent features an advanced RAG pipeline with:

- **Query Rewriting**: Generate multiple query variations for better retrieval
- **HyDE (Hypothetical Document Embedding)**: Generate hypothetical answers to improve retrieval
- **Hybrid Retrieval**: Combine vector search and BM25 keyword search
- **ColBERT-style Retrieval**: Token-level similarity matching
- **CrossEncoder Reranking**: Fine-grained relevance scoring
- **Knowledge Graph Verification**: Entity-based confidence scoring
- **Context Compression**: Smart context selection and compression

## Tools

### Built-in Tools

- `web_search` - Web search capability
- `code_interpreter` - Python code execution in sandbox
- `doc_parser` - Document parsing (PDF, Word, etc.)
- `image_gen` - Image generation
- `amap_weather` - Weather information
- And more...

### Custom Tools

You can easily add custom tools:

```python
from docucode_agent.tools.base import BaseTool, register_tool
import json5

@register_tool('my_custom_tool')
class MyCustomTool(BaseTool):
    description = 'Description of what this tool does.'
    parameters = [{
        'name': 'param1',
        'type': 'string',
        'description': 'Parameter description',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        args = json5.loads(params)
        # Your tool logic here
        return json5.dumps({'result': 'success'})
```

## FAQ

### How to use the Code Interpreter?

The Code Interpreter requires Docker to be installed and running. The first run will build the Docker image, which may take some time depending on your network.

### How to deploy my own model service?

You can deploy Qwen models using vLLM or Ollama for OpenAI-compatible API service. See Qwen documentation for details.

### How to handle very long documents?

DocuCode-Agent provides optimized RAG solutions for long documents, capable of handling 1M+ token contexts efficiently.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built upon [Qwen-Agent](https://github.com/QwenLM/Qwen-Agent) by Alibaba Group
- Uses Qwen models from Alibaba Cloud's DashScope

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## Disclaimer

The Docker container-based code interpreter mounts only the specified working directory and implements basic sandbox isolation, but should still be used with caution in production environments.
