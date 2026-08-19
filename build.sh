#!/bin/bash

EXEC_NAME="wine-linux-shortcut-maker-z"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
DESKTOP_FILE_NAME="wine-linux-shortcut-maker-z.desktop"

echo "Iniciando a construcao do Wine Linux Shortcut Maker Z..."

if [ -f "wine-linux-shortcut-maker-z.py" ]; then
    SCRIPT_NAME="wine-linux-shortcut-maker-z.py"
elif [ -f "Wine_Linux_Shortcut_Maker_Z.py" ]; then
    SCRIPT_NAME="Wine_Linux_Shortcut_Maker_Z.py"
elif [ -f "wine_linux_shortcut_maker_z.py" ]; then
    SCRIPT_NAME="wine_linux_shortcut_maker_z.py"
else
    echo "Erro: O arquivo do script Python nao foi encontrado."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"

# Remove stale files from old builds
rm -f "$HOME/.local/bin/$EXEC_NAME"
rm -f "$APP_DIR/$DESKTOP_FILE_NAME"
rm -f "$DESKTOP_DIR/$DESKTOP_FILE_NAME"

mkdir -p "$APP_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

echo "Instalando icone..."
cat > "$ICON_DIR/$EXEC_NAME.svg" << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 110 148" width="256" height="256">
  <path d="M22 10 L88 10 Q78 62 55 80 Q32 62 22 10 Z"
        fill="none" stroke="#E53935" stroke-width="7" stroke-linejoin="round"/>
  <line x1="55" y1="80" x2="55" y2="128"
        stroke="#E53935" stroke-width="7" stroke-linecap="round"/>
  <line x1="30" y1="136" x2="80" y2="136"
        stroke="#E53935" stroke-width="7" stroke-linecap="round"/>
</svg>
SVGEOF

chmod +x "$SCRIPT_PATH"

echo "Adicionando ao Menu do Sistema..."
cat > "$APP_DIR/$DESKTOP_FILE_NAME" << DESKTOPEOF
[Desktop Entry]
Name=Wine Linux Shortcut Maker Z
Comment=Generate shortcuts for Windows programs in Linux
Exec=python3 $SCRIPT_PATH
Path=$SCRIPT_DIR
Icon=$ICON_DIR/$EXEC_NAME.svg
Terminal=false
Type=Application
Categories=Utility;Wine;System;
NoDisplay=false
X-BigLinux-SoftwareRender=false
DESKTOPEOF
chmod +x "$APP_DIR/$DESKTOP_FILE_NAME"

echo "Criando atalho na Area de Trabalho..."
cp "$APP_DIR/$DESKTOP_FILE_NAME" "$DESKTOP_DIR/$DESKTOP_FILE_NAME"
chmod 755 "$DESKTOP_DIR/$DESKTOP_FILE_NAME"

if command -v gio &> /dev/null; then
    gio set "$DESKTOP_DIR/$DESKTOP_FILE_NAME" metadata::trusted true 2>/dev/null
fi

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR" &> /dev/null
fi

if command -v kbuildsycoca6 &> /dev/null; then
    kbuildsycoca6 &> /dev/null
elif command -v kbuildsycoca5 &> /dev/null; then
    kbuildsycoca5 &> /dev/null
fi

echo "Concluido!"
