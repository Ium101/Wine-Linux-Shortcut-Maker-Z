#!/bin/bash

EXEC_NAME="wine-linux-shortcut-maker-z"
LOCAL_OUTPUT_NAME="Wine Linux Shortcut Maker Z"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"
DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")

echo "⚙️ Iniciando a construção..."

if [ -f "Wine_Linux_Shortcut_Maker_Z.py" ]; then
    SCRIPT_NAME="Wine_Linux_Shortcut_Maker_Z.py"
elif [ -f "wine_linux_shortcut_maker_z.py" ]; then
    SCRIPT_NAME="wine_linux_shortcut_maker_z.py"
else
    echo "❌ Erro: O arquivo do script Python não foi encontrado."
    exit 1
fi

mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# ── EMBED ICON ────────────────────────────────────────────────────────────────
echo "🖼️ Instalando ícone..."
cat > "$ICON_DIR/$EXEC_NAME.svg" << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 110 148" width="256" height="256">
  <!-- back rectangle -->
  <rect x="24" y="24" width="82" height="116" rx="10" fill="none" stroke="#E53935" stroke-width="8"/>
  <!-- front rectangle -->
  <rect x="4" y="4" width="82" height="116" rx="10" fill="none" stroke="#E53935" stroke-width="8"/>
</svg>
SVGEOF
ICON_SETTING="$ICON_DIR/$EXEC_NAME.svg"
# ─────────────────────────────────────────────────────────────────────────────

echo "📦 Gerando executável..."
echo '#!/usr/bin/env python3' > "./$LOCAL_OUTPUT_NAME"
cat "$SCRIPT_NAME" >> "./$LOCAL_OUTPUT_NAME"
chmod +x "./$LOCAL_OUTPUT_NAME"
cp "./$LOCAL_OUTPUT_NAME" "$BIN_DIR/$EXEC_NAME"

DESKTOP_ENTRY_CONTENT="[Desktop Entry]
Name=Wine Linux Shortcut Maker Z
Comment=Generate shortcuts for Windows programs in Linux
Exec=$BIN_DIR/$EXEC_NAME
Icon=$ICON_SETTING
Terminal=false
Type=Application
Categories=Utility;Wine;
"

echo "$DESKTOP_ENTRY_CONTENT" > "$APP_DIR/$EXEC_NAME.desktop"
chmod +x "$APP_DIR/$EXEC_NAME.desktop"

DESKTOP_FILE_PATH="$DESKTOP_DIR/$EXEC_NAME.desktop"
echo "$DESKTOP_ENTRY_CONTENT" > "$DESKTOP_FILE_PATH"
chmod 755 "$DESKTOP_FILE_PATH"

if command -v gio &> /dev/null; then
    gio set "$DESKTOP_FILE_PATH" metadata::trusted true 2>/dev/null
fi

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR" &> /dev/null
fi

echo "✅ Concluído!"
