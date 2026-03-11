# Agente Simões - The clumsy AI agent.

<img src="agent-simoes.png" alt="Original">

## This is a simple, limit and clumsy agent.

## Features

### Session Management:
- Persistent Command History: Access previous commands easily with the "Up" arrow key.
- Session Transparency: View current session status or clear prompt history at any time.

### Context:
- Smart Context Loading: Automatically read and analyze files to provide relevant context.
- Live Token Counter: Monitor usage in real-time to manage limits effectively.
- Simple Parser: Efficient processing of inputs for faster response times.

### Safety & Control:
- Permission-Based Actions: Always asks for user authorization before executing sensitive tasks.
- Visual File Diffs: Review precise changes in files before applying edits.

### File System Operations (Automatically parsed):
The agent uses special tags in its responses:
- `[MKDIR:name]` - Create directory
- `[CREATE:name]content[END]` - Create/write file
- `[DELETE:name]` - Remove file or directory

## Architecture:

- **Entry Point**: `agent_simoes.py` connects to local llama-server via OpenAI-compatible API
- **State Management**: Maintains conversation session in memory using list of messages
- **Input History**: Uses readline for command history (saved to `~/.qwen_agent_history`)
- **File Operations**: Regex-based parsing of AI responses to execute file system commands
- **Feedback Loop**: Spinner class for visual progress indication during AI inference

##  About:
I chose the name **Agene Simões** as a tribute to the legendary character played by Portuguese comedian **Marco Horácio**. In Portuguese pop culture, Agente Simões is the ultimate **clumsy, bumbling, or "hot mess" character** much like this agent! lol.

Agente Simões is a officer who takes himself incredibly seriously. He constantly tries to project an image of a tough, highly disciplined "super-cop," but in reality, he is hilariously incompetent and always ends up in absurd situations.

By naming this after him, I’m leaning into that same "tough-but-clumsy" energy. It’s a self-deprecating nod to the fact that while the agent is "on duty" to handle tasks, it has a quirky, human-like side that doesn't take itself too seriously.

> **Fun Fact:** Marco Horácio actually drew inspiration from the classic ***Police Academy*** movies to create the character. You can see that same slapstick spirit in Agente Simões, an officer who looks like he's in charge but is basically a walking disaster!

## Requirements:

- llama-server
- Qwen 2.5 7B (tested model) or Qwen 3.5 9B

## Installation
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
## Running llama-server
The agent expects llama-server to be running independently:

### Qwen 2.5 7B

```bash
llama-server --model qwen2.5-7b-coder.gguf \
  --alias "Qwen 2.5" \
  --threads 8 \
  --ctx-size 32768 \
  --port 8001 \
  --n-gpu-layers 30 \
  --temp 0.0 \
  --top-k 1 \
  --jinja
```

### Qwen 3.5 9B

```bash
llama-server --model qwen3.5-9B-UD-Q4_K_XL.gguf \
  --alias "Qwen 3.5" \
  --threads 8 \
  --port 8001 \
  --fit on \
  --seed 1337 \
  --temp 1.0 \
  --top-k 20 \
  --top-p 0.8 \
  --min-p 0.0 \
  --ctx-size 32768 \
  --presence_penalty 1.5 \
  --flash-attn on \
  --chat-template-file qwen3.5_chat_template.jinja
```
