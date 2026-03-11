import os
import re
import openai
import threading
import sys
import time
import shutil
import subprocess
import difflib

# ANSI color codes
class Colors:
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKCYAN    = '\033[96m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    YELLOW    = '\033[93m'
    YELLOW_BRIGHT = '\033[38;5;226m'

# Run llama server before running this script.
# Example:
# llama-server --model /home/$USER/gguf_models/coding/qwen2.5-coder-14b-instruct-q8_0.gguf --alias "Qwen" --threads 8 --ctx-size 32768 --port 8001 --n-gpu-layers 30 --temp 0.0 --top-k 1 --jinja

# --- SETTINGS ---
DEFAULT_MODEL_NAME = "Qwen-7B-Coder"
BASE_URL = "http://127.0.0.1:8001/v1"
MAX_CHARS = 60000  # Safety limit for context size

# --- READLINE HISTORY (melhorado) ---
try:
    import readline
except ImportError:
    readline = None

histfile = os.path.join(os.path.expanduser("~"), ".agent_simoes_history")

if readline is not None:
    readline.set_history_length(2000)  # aumentar capacidade do histórico
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"{Colors.WARNING}Aviso: não foi possível ler histórico: {e}{Colors.ENDC}")

    def save_history():
        if readline is not None:
            try:
                readline.write_history_file(histfile)
            except Exception as e:
                print(f"{Colors.WARNING}Erro ao salvar histórico: {e}{Colors.ENDC}")

    import atexit
    atexit.register(save_history)

# Initialize OpenAI client pointing to local server
client = openai.OpenAI(base_url=BASE_URL, api_key="none")

def get_active_model():
    """Fetches the actual model alias from the local llama-server."""
    try:
        models = client.models.list()
        return models.data[0].id
    except Exception:
        return DEFAULT_MODEL_NAME

MODEL_ID = get_active_model()

# --- SPINNER ---
class Spinner:
    """Simple CLI spinner to show progress during AI inference."""
    def __init__(self, message=f"{MODEL_ID} is thinking..."):
        self.message = message
        self.stop_running = False
        self.thread = None

    def _animate(self):
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while not self.stop_running:
            sys.stdout.write(f"\r{Colors.OKCYAN}{chars[idx % len(chars)]}{Colors.ENDC} {self.message}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 20) + "\r")

    def __enter__(self):
        self.stop_running = False
        self.thread = threading.Thread(target=self._animate)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running = True
        if self.thread:
            self.thread.join()

def list_files():
    """Returns a formatted string of the current directory contents."""
    try:
        items = os.listdir(".")
        if not items:
            return "Empty"
        return "\n".join([f" - {'[DIR]' if os.path.isdir(i) else '[FILE]'} {i}" for i in items])
    except Exception as e:
        return str(e)
    
def parse_and_execute(ai_text):
    """Parses markdown code blocks and special tags from AI response."""
    if not ai_text:
        return False

    action_taken = False

    # Special command matches
    mkdir_matches = re.findall(r"\[MKDIR:\s*([^\]]+)\]", ai_text, re.I)
    delete_dir_matches = re.findall(r"\[DELETE_DIR:\s*([^\]]+)\]", ai_text, re.I)
    file_matches = re.findall(r"\[FILE:\s*([^\]]+)\]", ai_text, re.I)
    delete_file_matches = re.findall(r"\[DELETE_FILE:\s*([^\]]+)\]", ai_text, re.I)

    # Files from code blocks using new [@FILE: path] format
    files_to_create = []

    # Find all instances of [@FILE: path] followed by a code block
    # This regex captures the path and the content of the block that follows
    blocks = re.findall(
        r'\[@FILE:\s*([^\]]+)\]\s*\n```(?:\w+)?\s*\n(.*?)\n```',
        ai_text,
        re.DOTALL | re.IGNORECASE
    )

    for path_match, content_block in blocks:
        path = path_match.strip()
        path = os.path.normpath(path)

        if path and path not in ('.', '..', '/', ''):
            # Clean up the content (remove leading/trailing blank lines)
            content = content_block.strip()
            files_to_create.append((path, content))
        else:
            print(f"{Colors.WARNING}Invalid path in [@FILE: ...]: '{path_match}'{Colors.ENDC}")

    # If no blocks found with the new format, you can optionally fall back to old format
    # (but for now we assume the model follows the new instructions)
    #if not files_to_create:
        #print(f"{Colors.WARNING}No files proposed using [@FILE: ...] format.{Colors.ENDC}")

    # MKDIR ────────────────────────────────────────────────
    for folder in mkdir_matches:
        folder = folder.strip().strip("'\"[]")
        if folder:
            print(f"{Colors.WARNING}\n→ Create directory '{folder}'?{Colors.ENDC} (y/n): ", end="")
            confirm = input().lower().strip()
            if confirm in ('y', 'yes'):
                try:
                    os.makedirs(folder, exist_ok=True)
                    print(f"{Colors.OKGREEN}Created directory: {folder}{Colors.ENDC}")
                    action_taken = True
                except Exception as e:
                    print(f"{Colors.FAIL}Error creating directory: {e}{Colors.ENDC}")

    # DELETE_DIR ───────────────────────────────────────────
    for target in delete_dir_matches:
        target = target.strip().strip("'\"[]")
        if os.path.exists(target):
            print(f"{Colors.FAIL}\n→ DELETE '{target}'?{Colors.ENDC} (y/n): ", end="")
            confirm = input().lower().strip()
            if confirm in ('y', 'yes'):
                try:
                    if os.path.isdir(target):
                        shutil.rmtree(target)
                    else:
                        os.remove(target)
                    print(f"{Colors.OKGREEN}Removed: {target}{Colors.ENDC}")
                    action_taken = True
                except Exception as e:
                    print(f"{Colors.FAIL}Error removing: {e}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}Cannot delete: {target} does not exist{Colors.ENDC}")

    # FILE creation via [FILE: path] tag (empty file) ──────
    for path in file_matches:
        path = os.path.normpath(path.strip().strip("'\"[]"))
        if path and path not in ('.', '..', '/'):
            print(f"\n{Colors.OKBLUE}AI proposes to create file: {Colors.BOLD}{path}{Colors.ENDC}")
            confirm = input(f"{Colors.WARNING}Create this file? (y/n): {Colors.ENDC}").lower().strip()
            if confirm in ('y', 'yes'):
                dir_path = os.path.dirname(path)
                if dir_path and dir_path != '.':
                    try:
                        os.makedirs(dir_path, exist_ok=True)
                    except Exception as e:
                        print(f"{Colors.FAIL}Error creating directory: {e}{Colors.ENDC}")
                        continue
                try:
                    open(path, 'w').close()  # create empty file
                    print(f"{Colors.OKGREEN}Created empty file: {path}{Colors.ENDC}")
                    action_taken = True
                except Exception as e:
                    print(f"{Colors.FAIL}Error creating file: {e}{Colors.ENDC}")

    # DELETE_FILE ──────────────────────────────────────────
    for target in delete_file_matches:
        target = os.path.normpath(target.strip().strip("'\"[]"))
        if os.path.exists(target):
            if os.path.isdir(target):
                print(f"{Colors.WARNING}{target} is a directory. Use [DELETE_DIR] instead.{Colors.ENDC}")
                continue
            print(f"{Colors.FAIL}\n→ DELETE file '{target}'?{Colors.ENDC} (y/n): ", end="")
            confirm = input().lower().strip()
            if confirm in ('y', 'yes'):
                try:
                    os.remove(target)
                    print(f"{Colors.OKGREEN}Deleted file: {target}{Colors.ENDC}")
                    action_taken = True
                except Exception as e:
                    print(f"{Colors.FAIL}Error deleting file: {e}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}File not found: {target}{Colors.ENDC}")

    # Files from code blocks (preferred method) ───────────
    if files_to_create:
        # Phase 1: Show diffs for files that already exist ──────────────
        print(f"\n{Colors.WARNING}Checking for existing files...{Colors.ENDC}")
        existing_files = []  # list of indices that already exist
        diffs_shown = False

        for i, (path, new_content) in enumerate(files_to_create, 1):
            path = os.path.normpath(path)
            if os.path.exists(path) and os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        old_content = f.read()
                except Exception as e:
                    print(f"{Colors.FAIL}Could not read {path}: {e}{Colors.ENDC}")
                    continue

                if old_content == new_content:
                    print(f"{Colors.OKCYAN} {i}. {path} → already identical, no change needed{Colors.ENDC}")
                    continue

                # Generate unified diff
                diff_lines = difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    n=3
                )
                diff_text = "".join(diff_lines).rstrip()

                print(f"\n{Colors.WARNING}File {Colors.BOLD}{path}{Colors.ENDC} already exists.")
                print(f"{Colors.WARNING}Differences (unified diff):{Colors.ENDC}")
                print("─" * 70)

                # Color the diff lines
                colored_diff = []
                for line in diff_text.splitlines():
                    if line.startswith('+'):
                        colored_diff.append(f"{Colors.OKGREEN}{line}{Colors.ENDC}")
                    elif line.startswith('-'):
                        colored_diff.append(f"{Colors.FAIL}{line}{Colors.ENDC}")
                    elif line.startswith('@@'):
                        colored_diff.append(f"{Colors.OKCYAN}{line}{Colors.ENDC}")
                    else:
                        colored_diff.append(line)

                print("\n".join(colored_diff))
                print("─" * 70)

                existing_files.append(i)
                diffs_shown = True

        if not diffs_shown:
            print(f"{Colors.OKCYAN}No existing files would be modified.{Colors.ENDC}")
        elif existing_files:
            print(f"\n{Colors.WARNING}The files above (marked with numbers) already exist and would be overwritten.{Colors.ENDC}")

        # Phase 2: Ask the user which files to create ───────────────────
        print(f"\n{Colors.OKBLUE}Proposed files to create/update:{Colors.ENDC}")
        for i, (path, content) in enumerate(files_to_create, 1):
            size_str = f"{len(content)} bytes" if content else "empty"
            print(f" {Colors.BOLD}{i}. {path}{Colors.ENDC} ({size_str})")

        print(f"\n{Colors.WARNING}Create/update files?{Colors.ENDC} (all / none / numbers e.g. 1,3): ", end="")
        choice = input().lower().strip()

        if choice == 'none':
            print(f"{Colors.OKCYAN}No files created.{Colors.ENDC}")
            return action_taken

        selected_indices = []
        if choice == 'all':
            selected_indices = list(range(len(files_to_create)))
        else:
            try:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip().isdigit()]
                selected_indices = [idx for idx in selected_indices if 0 <= idx < len(files_to_create)]
            except ValueError:
                print(f"{Colors.FAIL}Invalid selection.{Colors.ENDC}")
                return action_taken

        # Create / update selected files ────────────────────────────────
        for idx in selected_indices:
            path, new_content = files_to_create[idx]
            path = os.path.normpath(path)

            dir_path = os.path.dirname(path)
            if dir_path and dir_path != '.':
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    print(f"{Colors.FAIL}Failed to create dir for {path}: {e}{Colors.ENDC}")
                    continue

            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                if idx + 1 in existing_files:
                    print(f"{Colors.OKGREEN}Updated: {path}{Colors.ENDC}")
                else:
                    print(f"{Colors.OKGREEN}Created: {path}{Colors.ENDC}")
                action_taken = True
            except Exception as e:
                print(f"{Colors.FAIL}Failed to write {path}: {e}{Colors.ENDC}")

    return action_taken


def start_msg():
    msg = """
                    ........                   
            .........oooooo........            
       ............ooo....oxo............      
    ...............ooo....oxo...............   
  .....................oo....................  
   .........................................   
       .....oooooooooooooooooooooooo....       
       oooooo......................ooooo.      
          .o........................o.         
       .oxo...oooxxxxxxxxxxxxxoooo..ooxo       
     ooo..........x@@@@@@@@@x..........ooo     
    oo.....      .o@@@@@@@@@x...  .......ox.   
  .xxo...oxooooo...x@@@@@@@xo..ooxxooo...oxx.  
  xxo.o@@xx@@xxxxo..oxxooxx..o@@@x@@xxxoo..xx. 
 oo...x@@@@x@@xxxxo.........ox@@@@xx@@xxx...oo.
 .....xx@@@@@x@@xxx..oxxxo..oxx@@@@@x@@xxo.... 
.xoo..oxxx@@@@@x@@o..xxxxxo..xxxx@@@@@x@@...oxo
.xxxo..oxxxx@@@@xo..xxxxxxx...oxxxx@@@@x..oxxxo
.xxxxxo...oooooo..oxxxxxxxxxo...oooooo...oxxxx.
 oxxxxxxoooooooox@xxxxxxxxxxxxxooooooooxxxxxxx 
 .xxxxxxx@@xx@@@@xxxxxxxxxxxxx@@@@@x@@@xxxxxxo 
  oxxxxxxxx.ooxoo.ooxxxxxxxooo.oxxo.x@xxxxxxx  
   oxxxxxxxo......  .oxxxo.   .....oxxxxxxxo   
    .xxxxxxxo......................oxxxxxxo    
      oxxxxxxxooo.....oxoo....ooooxxxxxxo      
        .xxxxxxxxxxxxxxxxxxxxxxxxxxxxx.        
            xxxxxxxxxxxxxxxxxxxxxxx.           
                 oxxxxxxxxxxxo.

            Agente Simões                   
"""
    print(f'{Colors.YELLOW_BRIGHT}{msg}')

# MAIN LOOP ────────────────────────────────────────────────────────
start_msg()
print(f"{Colors.OKGREEN}Active Model: {MODEL_ID}{Colors.ENDC}")
print("Commands: !shell_cmd | /read file_path | /session | /clear | /exit")

# System prompt
session = [
    {
        "role": "system",
        "content": (
            "You are a helpful Linux terminal coding assistant.\n\n"

            "IMPORTANT RULE – ALWAYS FOLLOW THIS FIRST:\n"
            "When you want to propose or create or update a file, you MUST start with:\n"
            "[@FILE: relative/path/to/file.ext]\n"
            "on its own line, and ONLY AFTER THAT you put the code block.\n"
            "Example 1:\n"
            "[@FILE: hello.sh]\n"
            "```bash"
            "echo \"Hello\"\n"
            "```\n\n"
            "Example 2:\n"
            "[@FILE: main.py]\n"
            "```python\n"
            "print('Oi')\n"
            "```\n\n"

            "When proposing or creating files:\n"
            "• ALWAYS use the format above: [@FILE: path] then code block\n"
            "• Use correct language after ```\n"
            "• Multiple files = multiple separate [@FILE: ...] + blocks\n\n"

            "When the user writes @filename (e.g. @main.py or @pasta/arquivo.sh):\n"
            "- Understand @ as a reference marker\n"
            "- In your response, use ONLY the path WITHOUT the leading @ in the [@FILE: ...] line\n"
            "- Example: if user says \"@hello.sh\", respond with [@FILE: hello.sh] NOT [@FILE: @hello.sh]\n\n"

            "Special commands (use only when explicitly needed):\n"
            "• Create folder:  [MKDIR: relative/path]\n"
            "• Delete folder:  [DELETE_DIR: relative/path]\n"
            "• Delete file:    [DELETE_FILE: relative/path]\n\n"

            "Answer concisely and technically.\n\n"
        )
    }
]


def print_session():
    """Prints all messages in the current session in a readable way."""
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER} CURRENT SESSION HISTORY ".center(70, "=") + Colors.ENDC)
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")
    
    for i, msg in enumerate(session, 1):
        role = msg["role"].upper()
        content = msg["content"]
        lines = content.splitlines()
        preview = "\n".join(lines[:6]) if len(lines) > 6 else content
        if len(lines) > 6:
            preview += f"\n... ({len(lines)-6} more lines)"
            
        print(f"[{i}] {Colors.BOLD}{role}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'-' * (len(role) + 4)}{Colors.ENDC}")
        print(preview)
        print("\n")
    
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")


def count_tokens_via_api(messages, base_url=BASE_URL):
    import requests
    
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "max_tokens": 1  # only count
    }
    
    try:
        response = requests.post(f"{base_url}/chat/completions", json=payload)
        if response.status_code == 200:
            usage = response.json().get("usage", {})
            return usage.get("prompt_tokens", 0)
        else:
            print("Erro counting tokens via API:", response.text)
            return None
    except Exception as e:
        print("API tokens count fail:", e)
        return None
    

# Main interaction loop
try:
    while True:
        try:
            tokens = count_tokens_via_api(session)
            if tokens is not None:
                print("\n\n")
                print(f"Tokens: {tokens}")
                print("")

            #user_input = input(f"\n{Colors.OKBLUE}👤 >{Colors.ENDC} ").strip()
            user_input = input("👤 > ").strip() # no color to fix multiline


            if user_input.lower() == "/exit":
                break

            # Automatically detect and load files referenced with @filename
            import re

            # Find patterns like @some/file.py or @file.txt
            # (supports simple relative paths, with or without /)
            file_refs = re.findall(r'@([^\s<>"\'`]+)', user_input)

            added_context = []

            for ref in file_refs:
                # ref can be "main.py", "folder/test.sh", etc.
                #filepath = ref.strip()
                filepath = ref.strip().lstrip('@').strip()

                # Try to resolve the relative path from the current working directory
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read().rstrip()

                        # Choose language for syntax highlighting (optional but improves readability)
                        ext = os.path.splitext(filepath)[1].lstrip('.').lower()
                        lang = ext if ext in ['py', 'js', 'ts', 'sh', 'bash', 'md', 'yaml', 'yml', 'json', 'html', 'css'] else ''

                        context_msg = (
                            f"Current content of file @{filepath}:\n\n"
                            f"```{lang}\n"
                            f"{content}\n"
                            f"```"
                        )

                        # Append to session history as a user message 
                        # (you can change to "system" if you prefer it as permanent context)
                        session.append({"role": "user", "content": context_msg})
                        added_context.append(filepath)

                        print(f"{Colors.OKGREEN}Added to context: @{filepath}{Colors.ENDC}")

                    except Exception as e:
                        print(f"{Colors.FAIL}Error reading @{filepath}: {e}{Colors.ENDC}")
                else:
                    print(f"{Colors.WARNING}File not found: @{filepath}{Colors.ENDC}")

            # If we added any context, show a visual separator so the user doesn't get lost
            if added_context:
                print(f"{Colors.OKCYAN}───────────────────────────────────────────────{Colors.ENDC}")

            if user_input.lower() == "/session":
                print_session()
                continue

            if user_input.lower() == "/clear":
                session = session[:1]
                print(f"{Colors.OKGREEN}Session cleared (system prompt kept).{Colors.ENDC}")
                continue

            if user_input.startswith("!"):
                cmd = user_input[1:].strip()
                print(f"{Colors.WARNING}Running: {cmd}{Colors.ENDC}")
                subprocess.run(cmd, shell=True)
                continue

            if not user_input:
                continue

            if user_input.startswith("/read "):
                fname = user_input[6:].strip()
                if os.path.exists(fname):
                    with open(fname, "r", encoding="utf-8") as f:
                        content = f.read()
                    if len(content) > MAX_CHARS:
                        print(f"{Colors.FAIL}⚠️ File content exceeds safety limit.{Colors.ENDC}")
                        continue
                    user_input = f"FILE CONTENT ({fname}):\n{content}\n\nTask: analyze or continue working with this file."
                else:
                    print(f"{Colors.FAIL}❌ File not found.{Colors.ENDC}")
                    continue

            session.append({"role": "user", "content": user_input})

            full_res = ""
            with Spinner(f"{MODEL_ID} is processing..."):
                response = client.chat.completions.create(
                    model=MODEL_ID,
                    messages=session,
                    temperature=0.0,
                    stream=True
                )
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content

            if full_res:
                print(f"\n{full_res}")
                action_taken = parse_and_execute(full_res)
                session.append({"role": "assistant", "content": full_res})

                #print(f"\n{Colors.OKCYAN}🔍 Current directory:{Colors.ENDC}\n{list_files()}")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.FAIL}[INTERRUPTED]{Colors.ENDC}")
            if input(f"{Colors.WARNING}Exit? (y/n): {Colors.ENDC}").lower().startswith('y'):
                break
            print(f"{Colors.OKGREEN}Continuing...{Colors.ENDC}\n")

except KeyboardInterrupt:
    print(f"\n{Colors.FAIL}Forced immediate exit.{Colors.ENDC}")
    sys.exit(0)

finally:
    print(f"\n{Colors.OKGREEN}Session closed.{Colors.ENDC}")
    print("Goodbye.")
