#!/bin/bash

# Define binary and path variables
EXEC_NAME="wine-linux-shortcut-maker-z"
LOCAL_OUTPUT_NAME="Wine Linux Shortcut Maker Z"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

# Use the python script logic to find the localized Desktop path robustly
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")

echo "⚙️ Iniciando a construção do Wine Linux Shortcut Maker Z..."

# 1. Busca inteligente pelo script Python (Updated logic for new name)
if [ -f "Wine_Linux_Shortcut_Maker_Z.py" ]; then
    SCRIPT_NAME="Wine_Linux_Shortcut_Maker_Z.py"
elif [ -f "wine_linux_shortcut_maker_z.py" ]; then
    SCRIPT_NAME="wine_linux_shortcut_maker_z.py"
else
    echo "❌ Erro: O arquivo do script Python não foi encontrado nesta pasta."
    echo "Certifique-se de que o arquivo se chama 'Wine_Linux_Shortcut_Maker_Z.py' ou 'wine_linux_shortcut_maker_z.py'."
    exit 1
fi

# 2. Cria as pastas do sistema caso não existam
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$DESKTOP_DIR"

# 3. GERA O PROGRAMA NA MESMA PASTA ATUAL (Local)
echo "📦 Gerando o executável na pasta atual..."
echo '#!/usr/bin/env python3' > "./$LOCAL_OUTPUT_NAME"
cat "$SCRIPT_NAME" >> "./$LOCAL_OUTPUT_NAME"
chmod +x "./$LOCAL_OUTPUT_NAME"

# 4. Copia o executável para a pasta de binários do sistema do usuário
echo "🚀 Instalando uma cópia no sistema (~/.local/bin)..."
cp "./$LOCAL_OUTPUT_NAME" "$BIN_DIR/$EXEC_NAME"

# 5. Define the content for the .desktop shortcut (Updated to new App Name)
DESKTOP_ENTRY_CONTENT="[Desktop Entry]
Name=Wine Linux Shortcut Maker Z
Comment=Gera atalhos configurados para programas .exe no Wine automaticamente
Exec=$BIN_DIR/$EXEC_NAME
Icon=wine
Terminal=false
Type=Application
Categories=Wine;Utility;System;
"

# 6. Cria o atalho no Menu de Aplicativos (Start Menu) sob a categoria "Wine"
echo "🖥️ Adicionando ao Menu do Sistema (Categoria: Wine)..."
echo "$DESKTOP_ENTRY_CONTENT" > "$APP_DIR/$EXEC_NAME.desktop"
chmod +x "$APP_DIR/$EXEC_NAME.desktop"

# 7. Cria o atalho na Área de Trabalho (Desktop) apenas na instalação
echo "🖼️ Criando atalho na Área de Trabalho..."
echo "$DESKTOP_ENTRY_CONTENT" > "$DESKTOP_DIR/$EXEC_NAME.desktop"
chmod +x "$DESKTOP_DIR/$EXEC_NAME.desktop"

# 8. Atualiza o banco de dados de atalhos do sistema
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR" &> /dev/null
fi

echo "======================================================="
echo "✅ Processo concluído com sucesso!"
echo "-> Executável criado na pasta atual: ./$LOCAL_OUTPUT_NAME"
echo "-> Instalado no Menu Iniciar (Categoria: Wine)"
echo "-> Atalho criado na Área de Trabalho"
echo "======================================================="