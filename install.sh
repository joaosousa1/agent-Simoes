#!/bin/bash

# Descobrir o caminho absoluto de onde este repo do agent_simoes foi clonado
REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_PATH="$REPO_DIR/venv/bin/activate"
AGENT_PY="$REPO_DIR/agent.py"
BIN_DIR="$HOME/.local/bin"
TARGET_SCRIPT="$BIN_DIR/agent"

# Criar pasta bin caso não exista
mkdir -p "$BIN_DIR"

echo "Instalando agente a partir de: $REPO_DIR"

# Criar o conteúdo do script wrapper
cat << EOF > "$TARGET_SCRIPT"
#!/bin/bash
# Ativar o ambiente virtual
source "$VENV_PATH"
# Executar o python passando o caminho absoluto do script, 
# mas o diretório de trabalho será o atual do terminal
python3 "$AGENT_PY" "\$@"
EOF

# Dar permissão de execução
chmod +x "$TARGET_SCRIPT"

echo "Sucesso! Agora pode usar o comando 'agent' em qualquer pasta."
echo "Certifique-se de que $BIN_DIR está no seu PATH."
