#!/usr/bin/env python3
import os
import sys
import glob
import tempfile
import configparser
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

# ── Theme palettes ────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":        "#232429",
        "fg":        "#FFFFFF",
        "sec_bg":    "#2D2E33",
        "btn_bg":    "#3A3D45",
        "btn_fg":    "#FFFFFF",
        "accent":    "#1976D2",
        "accent_hl": "#1565C0",
        "gray":      "#D0D3DA",
        "green":     "#81C995",
        "red":       "#F28B82",
        "orange":    "#F6BF26",
        "blue":      "#8AB4F8",
        "purple":    "#CF9FFF",
        "active_bg": "#555963",
        "theme_icon":"☀️",
    },
    "light": {
        "bg":        "#F2F2F7",
        "fg":        "#1C1C1E",
        "sec_bg":    "#E5E5EA",
        "btn_bg":    "#D1D1D6",
        "btn_fg":    "#1C1C1E",
        "accent":    "#1565C0",
        "accent_hl": "#0D47A1",
        "gray":      "#555558",
        "green":     "#2E7D32",
        "red":       "#C62828",
        "orange":    "#E65100",
        "blue":      "#1565C0",
        "purple":    "#6A1B9A",
        "active_bg": "#C7C7CC",
        "theme_icon":"🌙",
    },
}


# ── AppImage helpers ──────────────────────────────────────────────────────────
ICON_EXTS = (".png", ".svg", ".xpm")
GENERIC_ICON_NAMES = {"icon", "app", "application", "logo", "main", "default"}

# An icon read out of an AppImage is only written here when a shortcut is actually
# created (and only if the icon isn't already installed) — never on the Desktop
# and never inside the shared icon-theme folders.
APPIMAGE_ICON_DIR = Path.home() / ".local" / "share" / "wine_linux_shortcut_maker_z" / "icons"


def eh_appimage(header, nome_arquivo):
    """True if `header` (first bytes of a file) belongs to an AppImage.

    AppImage type 1/2 files are ELF binaries carrying the bytes 'A' 'I' 0x01/0x02
    at offset 8. An ELF file named *.AppImage is accepted as a fallback.
    """
    if header[:4] != b"\x7fELF":
        return False
    if header[8:10] == b"AI" and header[10:11] in (b"\x01", b"\x02"):
        return True
    return nome_arquivo.lower().endswith(".appimage")


def _dentro(base, alvo):
    """True if `alvo` really lives inside `base` (guards against hostile symlinks)."""
    base = os.path.realpath(base)
    alvo = os.path.realpath(alvo)
    return alvo == base or alvo.startswith(base + os.sep)


def _ext_imagem(dados):
    """Return '.png' / '.svg' / '.xpm' by sniffing the bytes, or None."""
    if dados[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    cabecalho = dados[:2048].lstrip().lower()
    if cabecalho.startswith(b"<svg") or (cabecalho.startswith(b"<?xml") and b"<svg" in cabecalho):
        return ".svg"
    if dados[:9] == b"/* XPM */":
        return ".xpm"
    return None


def _appimage_extract(caminho, padrao, tmp):
    """Ask the AppImage's own runtime to extract the files matching `padrao`.

    Output lands in <tmp>/squashfs-root. The working directory is a temp folder,
    so nothing is ever created next to the AppImage or on the Desktop.
    """
    try:
        subprocess.run(
            [caminho, "--appimage-extract", padrao],
            cwd=tmp, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _ler_desktop(arquivo):
    """Return (Name, Icon) from the [Desktop Entry] group of a .desktop file."""
    nome = icone = None
    dentro = False
    try:
        with open(arquivo, encoding="utf-8", errors="replace") as f:
            for linha in f:
                linha = linha.strip()
                if linha.startswith("["):
                    dentro = linha == "[Desktop Entry]"
                elif dentro and linha.startswith("Name=") and nome is None:
                    nome = linha[5:].strip() or None
                elif dentro and linha.startswith("Icon=") and icone is None:
                    icone = linha[5:].strip() or None
    except OSError:
        pass
    return nome, icone


def icone_instalado(nome):
    """True if `nome` already resolves to an icon on this system (theme or pixmaps)."""
    if not nome or nome.lower() in GENERIC_ICON_NAMES or os.sep in nome:
        return False
    bases = [
        Path.home() / ".local" / "share" / "icons",
        Path.home() / ".icons",
        Path("/usr/share/icons"),
        Path("/usr/share/pixmaps"),
    ]
    padroes = ["{n}{e}", "*/*/apps/{n}{e}", "*/apps/*/{n}{e}"]
    for base in bases:
        if not base.is_dir():
            continue
        for ext in ICON_EXTS:
            for padrao in padroes:
                if next(base.glob(padrao.format(n=glob.escape(nome), e=ext)), None):
                    return True
    return False


def _carregar_icone(info, raiz, rel):
    """Load <raiz>/<rel> into `info` if it is a real, reasonably sized image."""
    alvo = os.path.join(raiz, rel)
    try:
        if not (os.path.isfile(alvo) and _dentro(raiz, alvo)):
            return False
        if os.path.getsize(alvo) > 5 * 1024 * 1024:
            return False
        with open(alvo, "rb") as f:
            dados = f.read()
    except OSError:
        return False
    ext = _ext_imagem(dados)
    if not ext:
        return False
    info["icone_dados"], info["icone_ext"] = dados, ext
    return True


def extrair_dados_appimage(caminho):
    """Read the display name and icon out of an AppImage without leaving files behind.

    Returns a dict:
      nome             Name= from the AppImage's own .desktop (or None)
      icone_nome       Icon= name declared by that .desktop (or None)
      icone_instalado  True if that icon name already exists on this system,
                       so no icon file has to be written anywhere
      icone_dados      raw bytes of the embedded icon (only when not installed)
      icone_ext        '.png' / '.svg' / '.xpm' for icone_dados
    """
    info = {"nome": None, "icone_nome": None, "icone_instalado": False,
            "icone_dados": None, "icone_ext": None}

    with tempfile.TemporaryDirectory(prefix="wlsm_appimage_") as tmp:
        raiz = os.path.join(tmp, "squashfs-root")

        # 1) The AppImage's own .desktop gives us the app name and icon name.
        _appimage_extract(caminho, "*.desktop", tmp)
        candidatos = sorted(glob.glob(os.path.join(raiz, "*.desktop")))
        candidatos += sorted(glob.glob(os.path.join(raiz, "usr", "share", "applications", "*.desktop")))
        for arq in candidatos:
            if _dentro(raiz, arq):
                info["nome"], info["icone_nome"] = _ler_desktop(arq)
                break

        # 2) Icon already installed on the system? Then there is nothing to copy.
        if icone_instalado(info["icone_nome"]):
            info["icone_instalado"] = True
            return info

        # 3) Otherwise read it from inside the AppImage: .DirIcon, which is
        #    usually a symlink to the real image (follow it, extracting each hop).
        rel = ".DirIcon"
        for _ in range(4):
            _appimage_extract(caminho, rel, tmp)
            alvo = os.path.join(raiz, rel)
            if os.path.islink(alvo):
                destino = os.readlink(alvo)
                novo = os.path.normpath(os.path.join(os.path.dirname(rel), destino))
                if os.path.isabs(destino) or novo.startswith(".."):
                    break
                rel = novo
                continue
            _carregar_icone(info, raiz, rel)
            break

        # 4) ...or the file named by Icon= (name.png / name.svg / name.xpm).
        nome_icone = info["icone_nome"]
        if info["icone_dados"] is None and nome_icone and os.sep not in nome_icone:
            for ext in ICON_EXTS:
                _appimage_extract(caminho, nome_icone + ext, tmp)
                if _carregar_icone(info, raiz, nome_icone + ext):
                    break

    return info


class LinuxShortcutMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("Wine Linux Shortcut Maker Z")
        self.root.minsize(560, 0)
        self.root.eval('tk::PlaceWindow . center')
        self.root.resizable(True, True)

        # --- Load custom window icon ---
        try:
            caminho_icone_janela = Path.home() / ".local" / "share" / "icons" / "wine-linux-shortcut-maker-z.png"
            if caminho_icone_janela.exists():
                icone_img = tk.PhotoImage(file=str(caminho_icone_janela))
                self.root.iconphoto(True, icone_img)
        except Exception:
            pass

        # --- Persistent config paths (must come before _apply_palette) ---
        self.config_dir  = Path(__file__).resolve().parent
        self.config_file = self.config_dir / "config_sh.ini"

        # --- Load saved settings (theme + language + last path) ---
        settings = self._load_settings()
        self.current_theme = settings.get("theme", "dark")
        self._apply_palette()
        self.root.configure(bg=self.bg_color)

        # --- Executable type (restores the last manually-picked option) ---
        self.exe_type = tk.StringVar(value=settings.get("exe_type", "wine"))

        # --- Translation dictionary ---
        self.lang = settings.get("language", "en")
        self.texts = {
            "en": {
                "title": "Wine Linux Shortcut Maker Z",
                "subtitle": "Create perfect shortcuts for Windows & Linux applications",
                "type_label": "Executable Type:",
                "type_wine": "Windows (.exe via Wine)",
                "type_native": "Native Linux executable",
                "type_appimage": "Linux AppImage",
                "step1_wine": "1. Executable File:  \u2192 Detected as Windows/Wine",
                "step1_native": "1. Executable File:  \u2192 Detected as Linux native executable",
                "step1_appimage": "1. Executable File:  \u2192 Detected as Linux AppImage",
                "step1_default": "1. Executable File:",
                "no_file": "No file selected",
                "browse_wine": "Browse...",
                "browse_native": "Browse...",
                "step2": "2. Shortcut Name (Customizable):",
                "step3": "3. Program Icon:",
                "default_icon": "Default Wine icon",
                "default_icon_native": "No icon selected",
                "change_icon": "Change Icon",
                "btn_create": "🚀 Create Shortcut",
                "credits": "Made by Ium101",
                "lang_btn": "🇧🇷 Mudar para Português",
                "err_step1": "Please select an executable file in Step 1.",
                "err_empty_name": "The shortcut name cannot be empty.",
                "extracting": "Attempting to extract icon...",
                "ext_success": "✅ Original icon extracted successfully!",
                "ext_fail": "❌ Extraction failed. Using default.",
                "custom_icon": "Custom: ",
                "success_title": "Absolute Success!",
                "success_msg_wine":   "The program '{0}' was configured!\n\n✓ Shortcut created with Anti-Crash protection (EBADF).\n✓ Added to Start Menu and Desktop.",
                "success_msg_appimage": "The program '{0}' was configured!\n\n✓ AppImage shortcut created.\n✓ Added to Start Menu and Desktop.",
                "icon_reused": "✅ Icon already installed: {0}",
                "ext_success_appimage": "✅ Icon read from the AppImage!",
                "success_msg_native": "The program '{0}' was configured!\n\n✓ Native Linux shortcut created.\n✓ Added to Start Menu and Desktop.",
                "err_title": "Error",
                "err_msg": "A problem occurred while saving the shortcuts:\n{0}",
                "ask_exe": "Select the .exe file",
                "ask_native": "Select the Linux executable",
                "ask_icon": "Select an icon image",
                "args_label": "4. Extra Arguments (optional):",
                "args_placeholder": "e.g.  --no-sandbox  or  -f config.cfg",
                "cat_label": "5. Menu Category:",
                "categories": [
                    ("Utility",    "Utilities"),
                    ("Development","Development"),
                    ("Office",     "Office"),
                    ("Graphics",   "Graphics"),
                    ("Network",    "Internet"),
                    ("Game",       "Games"),
                    ("AudioVideo", "Multimedia"),
                    ("System",     "System"),
                    ("WebApps",    "Webapps"),
                ],
            },
            "pt": {
                "title": "Wine Linux Shortcut Maker Z",
                "subtitle": "Crie atalhos perfeitos para aplicativos Windows e Linux",
                "type_label": "Tipo de Executável:",
                "type_wine": "Windows (.exe via Wine)",
                "type_native": "Executável nativo Linux",
                "type_appimage": "AppImage Linux",
                "step1_wine": "1. Arquivo Executável:  \u2192 Detectado como Windows/Wine",
                "step1_native": "1. Arquivo Executável:  \u2192 Detectado como Executável nativo Linux",
                "step1_appimage": "1. Arquivo Executável:  \u2192 Detectado como AppImage Linux",
                "step1_default": "1. Arquivo Executável:",
                "no_file": "Nenhum arquivo selecionado",
                "browse_wine": "Procurar...",
                "browse_native": "Procurar...",
                "step2": "2. Nome do Atalho (Personalizável):",
                "step3": "3. Ícone do Programa:",
                "default_icon": "Ícone padrão do Wine",
                "default_icon_native": "Nenhum ícone selecionado",
                "change_icon": "Trocar Ícone",
                "btn_create": "🚀 Criar Atalho",
                "credits": "Feito por Ium101",
                "lang_btn": "🇺🇸 Switch to English",
                "err_step1": "Por favor, selecione um arquivo executável no Passo 1.",
                "err_empty_name": "O nome do atalho não pode ficar vazio.",
                "extracting": "Tentando extrair ícone...",
                "ext_success": "✅ Ícone original extraído com sucesso!",
                "ext_fail": "❌ Falha ao extrair. Usando padrão.",
                "custom_icon": "Personalizado: ",
                "success_title": "Sucesso Absoluto!",
                "success_msg_wine":   "O programa '{0}' foi configurado!\n\n✓ Atalho criado com proteção contra crash (EBADF).\n✓ Adicionado ao Menu Iniciar e Área de Trabalho.",
                "success_msg_appimage": "O programa '{0}' foi configurado!\n\n✓ Atalho de AppImage criado.\n✓ Adicionado ao Menu Iniciar e Área de Trabalho.",
                "icon_reused": "✅ Ícone já instalado: {0}",
                "ext_success_appimage": "✅ Ícone lido de dentro do AppImage!",
                "success_msg_native": "O programa '{0}' foi configurado!\n\n✓ Atalho nativo Linux criado.\n✓ Adicionado ao Menu Iniciar e Área de Trabalho.",
                "err_title": "Erro",
                "err_msg": "Ocorreu um problema ao salvar os atalhos:\n{0}",
                "ask_exe": "Selecione o arquivo .exe",
                "ask_native": "Selecione o executável Linux",
                "ask_icon": "Selecione uma imagem de ícone",
                "args_label": "4. Argumentos Extras (opcional):",
                "args_placeholder": "ex:  --no-sandbox  ou  -f config.cfg",
                "cat_label": "5. Categoria do Menu:",
                "categories": [
                    ("Utility",    "Utilitários"),
                    ("Development","Desenvolvimento"),
                    ("Office",     "Escritório"),
                    ("Graphics",   "Gráficos"),
                    ("Network",    "Internet"),
                    ("Game",       "Jogos"),
                    ("AudioVideo", "Multimídia"),
                    ("System",     "Sistema"),
                    ("WebApps",    "Webapps"),
                ],
            }
        }

        self.caminho_exe   = ""
        # Default icon-label state matches whichever type was restored above.
        self.caminho_icone = "wine" if self.exe_type.get() == "wine" else ""
        self.status_icone  = "default"
        self._icone_appimage = None   # (bytes, ext) read from an AppImage; written only on "Create"
        self.category      = tk.StringVar(value=settings.get("category", "Utility"))

        self._build_ui()
        self._freeze_width()

    def _freeze_width(self):
        """Pin the window to a width wide enough for the longest Step-1 label
        (the "Linux native executable" option, in either language) so switching
        between the three executable-type options never grows or shrinks the
        window — only a manual resize by the user changes it afterwards.
        """
        # Measure with a real, temporarily-packed Label rather than raw font.measure:
        # the actual widget's own padding/borderwidth add a few pixels that a plain
        # text measurement misses, and those pixels are exactly what got clipped.
        sonda = tk.Label(self.root, font=("Arial", 10, "bold"))
        largura_texto = 0
        for lang in ("en", "pt"):
            for key in ("step1_wine", "step1_native", "step1_appimage"):
                sonda.config(text=self.texts[lang][key])
                sonda.update_idletasks()
                largura_texto = max(largura_texto, sonda.winfo_reqwidth())
        sonda.destroy()

        self.root.update_idletasks()
        # +40 = the label's own pack padx=20 on each side; +12 extra safety margin.
        largura = max(self.root.winfo_reqwidth(), largura_texto + 40 + 12)
        altura = self.root.winfo_reqheight()
        self.root.geometry(f"{largura}x{altura}")
        self.root.minsize(largura, 0)
        # Freeze automatic resizing from content changes (radio selection, language,
        # theme); the window only changes size again if the user drags its edge.
        self.root.pack_propagate(False)

    # ── Theme helpers ─────────────────────────────────────────────────────────
    def _apply_palette(self):
        """Copy the active theme's colours into convenient self.* attributes."""
        p = THEMES[self.current_theme]
        self.bg_color    = p["bg"]
        self.fg_color    = p["fg"]
        self.sec_bg      = p["sec_bg"]
        self.btn_bg      = p["btn_bg"]
        self.btn_fg      = p["btn_fg"]
        self.btn_accent  = p["accent"]
        self.color_gray  = p["gray"]
        self.color_green = p["green"]
        self.color_red   = p["red"]
        self.color_orange= p["orange"]
        self.color_blue  = p["blue"]
        self.color_purple= p["purple"]

    # XDG category keys are language-independent (only display labels are translated)
    VALID_CATEGORIES = {"Utility", "Development", "Office", "Graphics", "Network", "Game", "AudioVideo", "System", "WebApps"}

    def _load_settings(self):
        """Load saved settings (theme + language + last browsed path + category) from config_sh.ini."""
        defaults = {"theme": "dark", "language": "en", "last_path": "", "category": "Utility", "exe_type": "wine"}
        try:
            if self.config_file.exists():
                parser = configparser.ConfigParser()
                parser.read(self.config_file, encoding="utf-8")
                section = parser["settings"] if parser.has_section("settings") else {}
                theme = section.get("theme", defaults["theme"])
                language = section.get("language", defaults["language"])
                last_path = section.get("last_path", defaults["last_path"])
                category = section.get("category", defaults["category"])
                exe_type = section.get("exe_type", defaults["exe_type"])
                if theme not in THEMES:
                    theme = defaults["theme"]
                if language not in ("en", "pt"):
                    language = defaults["language"]
                if category not in self.VALID_CATEGORIES:
                    category = defaults["category"]
                if exe_type not in ("wine", "native", "appimage"):
                    exe_type = defaults["exe_type"]
                return {"theme": theme, "language": language, "last_path": last_path,
                        "category": category, "exe_type": exe_type}
        except Exception:
            pass
        return defaults

    def _save_settings(self, **updates):
        """Persist current theme + language + last path + category to config_sh.ini.

        Any provided keyword overrides the corresponding in-memory value
        before saving (used for last_path/category, which aren't always
        in sync with self at call time).
        """
        try:
            current = self._load_settings()
            current["theme"] = self.current_theme
            current["language"] = self.lang
            current["category"] = self.category.get()
            current["exe_type"] = self.exe_type.get()
            current.update(updates)
            parser = configparser.ConfigParser()
            parser["settings"] = current
            with open(self.config_file, "w", encoding="utf-8") as f:
                parser.write(f)
        except Exception:
            pass

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_palette()
        self._save_settings()
        self._repaint_ui()

    def _repaint_ui(self):
        """Recolour every widget to match the new theme without rebuilding the UI."""
        p = THEMES[self.current_theme]

        # Root
        self.root.configure(bg=self.bg_color)

        # Top bar
        self.frame_top.configure(bg=self.bg_color)
        self.frame_controls.configure(bg=self.bg_color)
        self.btn_lang.config(
            bg=self.bg_color, fg=self.color_blue,
            activebackground=self.bg_color, activeforeground="white",
        )
        self.btn_theme.config(
            bg=self.bg_color, fg=self.color_orange,
            activebackground=self.bg_color, activeforeground="white",
            text=p["theme_icon"],
        )

        # Title / subtitle
        self.lbl_title.config(bg=self.bg_color, fg=self.fg_color)
        self.lbl_subtitle.config(bg=self.bg_color, fg=self.color_gray)

        # Executable type selector
        self.frame_type.configure(bg=self.bg_color)
        self.lbl_type.config(bg=self.bg_color, fg=self.fg_color)
        rb_cfg = dict(
            bg=self.bg_color, fg=self.fg_color,
            activebackground=self.bg_color, activeforeground=self.fg_color,
            selectcolor=self.sec_bg,
        )
        self.rb_wine.config(**rb_cfg)
        self.rb_native.config(**rb_cfg)
        self.rb_appimage.config(**rb_cfg)

        # Step 1 – exe
        self.lbl_step1.config(bg=self.bg_color, fg=self.fg_color)
        self.frame_exe.configure(bg=self.bg_color)
        self.lbl_exe.config(bg=self.bg_color)          # fg is dynamic; don't touch it
        self.btn_browse.config(
            bg=self.btn_bg, fg=self.btn_fg,
            activebackground=p["active_bg"], activeforeground=self.btn_fg,
        )

        # Step 2 – name entry
        self.lbl_step2.config(bg=self.bg_color, fg=self.fg_color)
        self.entry_nome.config(
            bg=self.sec_bg, fg=self.fg_color, insertbackground=self.fg_color,
        )

        # Step 3 – icon
        self.lbl_step3.config(bg=self.bg_color, fg=self.fg_color)
        self.frame_icone.configure(bg=self.bg_color)
        self.lbl_icone.config(bg=self.bg_color)        # fg is dynamic; don't touch it
        self.btn_icon.config(
            bg=self.btn_bg, fg=self.btn_fg,
            activebackground=p["active_bg"], activeforeground=self.btn_fg,
        )

        # Step 4 – extra args
        self.lbl_args.config(bg=self.bg_color, fg=self.fg_color)
        args_fg = self.color_gray if self._args_placeholder_active else self.fg_color
        self.entry_args.config(
            bg=self.sec_bg, fg=args_fg, insertbackground=self.fg_color,
        )

        # Step 5 – category dropdown
        self.lbl_cat.config(bg=self.bg_color, fg=self.fg_color)
        self.frame_cat.configure(bg=self.bg_color)
        self.opt_cat.config(
            bg=self.btn_bg, fg=self.btn_fg,
            activebackground=p["active_bg"], activeforeground=self.btn_fg,
        )
        self.opt_cat["menu"].config(
            bg=self.btn_bg, fg=self.btn_fg,
            activebackground=self.btn_accent, activeforeground="white",
        )

        # Create button
        self.btn_create.config(
            bg=self.btn_accent, fg="white",
            activebackground=p["accent_hl"], activeforeground="white",
        )

        # Credits
        self.lbl_credits.config(bg=self.bg_color, fg=self.color_gray)

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        p = THEMES[self.current_theme]

        btn_style = {
            "bg": self.btn_bg, "fg": self.btn_fg,
            "activebackground": p["active_bg"], "activeforeground": self.btn_fg,
            "relief": "ridge", "bd": 1,
        }

        # ── Credits (bottom) ─────────────────────────────────────────────────
        self.lbl_credits = tk.Label(self.root, text=self.texts[self.lang]["credits"],
                                    fg=self.color_gray, bg=self.bg_color, font=("Arial", 8))
        self.lbl_credits.pack(side="bottom", pady=10)

        # ── Top bar: language toggle + theme toggle ───────────────────────────
        self.frame_top = tk.Frame(self.root, bg=self.bg_color)
        self.frame_top.pack(fill="x", pady=10)

        self.frame_controls = tk.Frame(self.frame_top, bg=self.bg_color)
        self.frame_controls.pack(anchor="center")

        self.btn_lang = tk.Button(
            self.frame_controls, text=self.texts[self.lang]["lang_btn"],
            command=self.toggle_lang,
            bg=self.bg_color, fg=self.color_blue,
            activebackground=self.bg_color, activeforeground="white",
            relief="flat", cursor="hand2", font=("Arial", 9, "bold"),
        )
        self.btn_lang.pack(side="left", padx=(0, 10))

        self.btn_theme = tk.Button(
            self.frame_controls, text=p["theme_icon"],
            command=self.toggle_theme,
            bg=self.bg_color, fg=self.color_orange,
            activebackground=self.bg_color, activeforeground="white",
            relief="flat", cursor="hand2", font=("Arial", 11),
        )
        self.btn_theme.pack(side="left")

        # ── Title / subtitle ─────────────────────────────────────────────────
        self.lbl_title = tk.Label(self.root, text=self.texts[self.lang]["title"],
                                  font=("Arial", 14, "bold"), bg=self.bg_color, fg=self.fg_color)
        self.lbl_title.pack(pady=(0, 2))

        self.lbl_subtitle = tk.Label(self.root, text=self.texts[self.lang]["subtitle"],
                                     bg=self.bg_color, fg=self.color_gray, justify="center")
        self.lbl_subtitle.pack(pady=(0, 10), fill="x")
        self.lbl_subtitle.bind("<Configure>", lambda e: self.lbl_subtitle.config(wraplength=e.width - 20))

        # ── Executable type selector ──────────────────────────────────────────
        self.frame_type = tk.Frame(self.root, bg=self.bg_color)
        self.frame_type.pack(fill="x", padx=20, pady=(0, 8))

        self.lbl_type = tk.Label(self.frame_type, text=self.texts[self.lang]["type_label"],
                                 font=("Arial", 10, "bold"), bg=self.bg_color, fg=self.fg_color)
        self.lbl_type.pack(anchor="w")

        rb_style = {
            "bg": self.bg_color, "fg": self.fg_color,
            "activebackground": self.bg_color, "activeforeground": self.fg_color,
            "selectcolor": self.sec_bg, "relief": "flat", "cursor": "hand2",
        }

        self.rb_wine = tk.Radiobutton(self.frame_type, text=self.texts[self.lang]["type_wine"],
                                      variable=self.exe_type, value="wine",
                                      command=self.on_type_change, **rb_style)
        self.rb_wine.pack(anchor="w", padx=(16, 0))

        self.rb_native = tk.Radiobutton(self.frame_type, text=self.texts[self.lang]["type_native"],
                                        variable=self.exe_type, value="native",
                                        command=self.on_type_change, **rb_style)
        self.rb_native.pack(anchor="w", padx=(16, 0))

        self.rb_appimage = tk.Radiobutton(self.frame_type, text=self.texts[self.lang]["type_appimage"],
                                          variable=self.exe_type, value="appimage",
                                          command=self.on_type_change, **rb_style)
        self.rb_appimage.pack(anchor="w", padx=(16, 0))

        # ── Step 1: executable ────────────────────────────────────────────────
        self.lbl_step1 = tk.Label(self.root, text=self.texts[self.lang]["step1_default"],
                                  font=("Arial", 10, "bold"), bg=self.bg_color, fg=self.fg_color,
                                  anchor="w", justify="left")
        self.lbl_step1.pack(anchor="w", padx=20, fill="x")

        self.frame_exe = tk.Frame(self.root, bg=self.bg_color)
        self.frame_exe.pack(fill="x", padx=20, pady=5)

        self.lbl_exe = tk.Label(self.frame_exe, text=self.texts[self.lang]["no_file"],
                                fg=self.color_gray, bg=self.bg_color, justify="left", anchor="w")
        self.lbl_exe.pack(side="left", expand=True, fill="x")
        self.lbl_exe.bind("<Configure>", lambda e: self.lbl_exe.config(wraplength=e.width - 4))

        self.btn_browse = tk.Button(self.frame_exe, text=self.texts[self.lang]["browse_wine"],
                                    command=self.selecionar_exe, **btn_style)
        self.btn_browse.pack(side="right")

        # ── Step 2: name ──────────────────────────────────────────────────────
        self.lbl_step2 = tk.Label(self.root, text=self.texts[self.lang]["step2"],
                                  font=("Arial", 10, "bold"), bg=self.bg_color, fg=self.fg_color)
        self.lbl_step2.pack(anchor="w", padx=20, pady=(12, 0))

        self.entry_nome = tk.Entry(self.root, font=("Arial", 11), bg=self.sec_bg,
                                   fg=self.fg_color, insertbackground=self.fg_color, relief="flat")
        self.entry_nome.pack(fill="x", padx=20, pady=5)

        # ── Step 3: icon ─────────────────────────────────────────────────────
        self.lbl_step3 = tk.Label(self.root, text=self.texts[self.lang]["step3"],
                                  font=("Arial", 10, "bold"), bg=self.bg_color, fg=self.fg_color)
        self.lbl_step3.pack(anchor="w", padx=20, pady=(12, 0))

        self.frame_icone = tk.Frame(self.root, bg=self.bg_color)
        self.frame_icone.pack(fill="x", padx=20, pady=5)

        _icone_inicial = self.texts[self.lang]["default_icon"] if self.exe_type.get() == "wine" \
            else self.texts[self.lang]["default_icon_native"]
        self.lbl_icone = tk.Label(self.frame_icone, text=_icone_inicial,
                                  fg=self.color_gray, bg=self.bg_color, justify="left", anchor="w")
        self.lbl_icone.pack(side="left", expand=True, fill="x")
        self.lbl_icone.bind("<Configure>", lambda e: self.lbl_icone.config(wraplength=e.width - 4))

        self.btn_icon = tk.Button(self.frame_icone, text=self.texts[self.lang]["change_icon"],
                                  command=self.selecionar_icone_manual, **btn_style)
        self.btn_icon.pack(side="right")

        # ── Step 4: extra arguments ───────────────────────────────────────────
        self.lbl_args = tk.Label(self.root, text=self.texts[self.lang]["args_label"],
                                 font=("Arial", 10, "bold"), bg=self.bg_color, fg=self.fg_color)
        self.lbl_args.pack(anchor="w", padx=20, pady=(12, 0))

        self.entry_args = tk.Entry(self.root, font=("Arial", 10), bg=self.sec_bg,
                                   fg=self.color_gray, insertbackground=self.fg_color, relief="flat")
        self.entry_args.pack(fill="x", padx=20, pady=5)
        self.entry_args.insert(0, self.texts[self.lang]["args_placeholder"])
        self.entry_args.bind("<FocusIn>",  self._args_focus_in)
        self.entry_args.bind("<FocusOut>", self._args_focus_out)
        self._args_placeholder_active = True

        # ── Step 5: menu category ─────────────────────────────────────────────
        self.lbl_cat = tk.Label(self.root, text=self.texts[self.lang]["cat_label"],
                                font=("Arial", 10, "bold"), bg=self.bg_color, fg=self.fg_color)
        self.lbl_cat.pack(anchor="w", padx=20, pady=(12, 0))

        self.frame_cat = tk.Frame(self.root, bg=self.bg_color)
        self.frame_cat.pack(fill="x", padx=20, pady=5)

        self._cat_keys    = [k for k, _ in self.texts[self.lang]["categories"]]
        self._cat_labels  = [lbl for _, lbl in self.texts[self.lang]["categories"]]
        _initial_label = self._cat_labels[0]
        for _key, _lbl in self.texts[self.lang]["categories"]:
            if _key == self.category.get():
                _initial_label = _lbl
                break
        self._cat_display = tk.StringVar(value=_initial_label)

        self.opt_cat = tk.OptionMenu(self.frame_cat, self._cat_display, *self._cat_labels,
                                     command=self._on_cat_change)
        self.opt_cat.config(bg=self.btn_bg, fg=self.btn_fg,
                            activebackground=p["active_bg"], activeforeground=self.btn_fg,
                            highlightthickness=0, relief="ridge", bd=1,
                            font=("Arial", 10))
        self.opt_cat["menu"].config(bg=self.btn_bg, fg=self.btn_fg,
                                    activebackground=self.btn_accent,
                                    activeforeground="white")
        self.opt_cat.pack(side="left")

        # ── Create button ─────────────────────────────────────────────────────
        self.btn_create = tk.Button(self.root, text=self.texts[self.lang]["btn_create"],
                                    command=self.criar_atalho,
                                    font=("Arial", 11, "bold"), pady=8,
                                    bg=self.btn_accent, fg="white",
                                    activebackground=p["accent_hl"], activeforeground="white",
                                    relief="flat")
        self.btn_create.pack(pady=18)

    # ── Placeholder helpers ───────────────────────────────────────────────────
    def _args_focus_in(self, _event):
        if self._args_placeholder_active:
            self.entry_args.delete(0, tk.END)
            self.entry_args.config(fg=self.fg_color)
            self._args_placeholder_active = False

    def _args_focus_out(self, _event):
        if not self.entry_args.get().strip():
            self.entry_args.insert(0, self.texts[self.lang]["args_placeholder"])
            self.entry_args.config(fg=self.color_gray)
            self._args_placeholder_active = True

    def _get_args(self):
        """Return extra arguments, or empty string if placeholder is showing."""
        if self._args_placeholder_active:
            return ""
        return self.entry_args.get().strip()

    def _step1_key(self):
        """Translation key for the Step 1 label, based on the selected executable type."""
        return {"wine": "step1_wine", "appimage": "step1_appimage"}.get(self.exe_type.get(), "step1_native")

    # ── Type-change callback (manual override) ────────────────────────────────
    def on_type_change(self):
        t = self.texts[self.lang]
        is_wine = self.exe_type.get() == "wine"
        self._save_settings()

        # Show detection label in orange to signal manual override
        self.lbl_step1.config(
            text=t[self._step1_key()],
            fg=self.color_orange
        )

        # Reset icon to the appropriate default for the selected type.
        # Extraction only happens in selecionar_exe, after the user picks a file.
        if is_wine:
            self.caminho_icone = "wine"
            self.lbl_icone.config(text=t["default_icon"], fg=self.color_gray)
        else:
            self.caminho_icone = ""
            self.lbl_icone.config(text=t["default_icon_native"], fg=self.color_gray)
        self.status_icone = "default"
        self._icone_appimage = None

    # ── Language toggle ───────────────────────────────────────────────────────
    def toggle_lang(self):
        self.lang = "pt" if self.lang == "en" else "en"
        self._save_settings()
        t = self.texts[self.lang]
        is_wine = self.exe_type.get() == "wine"

        self.btn_lang.config(text=t["lang_btn"])
        self.lbl_title.config(text=t["title"])
        self.lbl_subtitle.config(text=t["subtitle"])
        self.lbl_type.config(text=t["type_label"])
        self.rb_wine.config(text=t["type_wine"])
        self.rb_native.config(text=t["type_native"])
        self.rb_appimage.config(text=t["type_appimage"])
        if self.caminho_exe:
            self.lbl_step1.config(text=t[self._step1_key()])
        else:
            self.lbl_step1.config(text=t["step1_default"], fg=self.fg_color)
        self.lbl_step2.config(text=t["step2"])
        self.lbl_step3.config(text=t["step3"])
        self.btn_icon.config(text=t["change_icon"])
        self.btn_create.config(text=t["btn_create"])
        self.lbl_credits.config(text=t["credits"])
        self.lbl_args.config(text=t["args_label"])

        if not self.caminho_exe:
            self.lbl_exe.config(text=t["no_file"])

        if self.status_icone == "default":
            self.lbl_icone.config(text=t["default_icon"] if is_wine else t["default_icon_native"])
        elif self.status_icone == "success":
            self.lbl_icone.config(text=t["ext_success_appimage"] if self._icone_appimage else t["ext_success"])
        elif self.status_icone == "reused":
            self.lbl_icone.config(text=t["icon_reused"].format(self.caminho_icone))
        elif self.status_icone == "fail":
            self.lbl_icone.config(text=t["ext_fail"])
        elif self.status_icone == "custom":
            self.lbl_icone.config(text=f"{t['custom_icon']}{os.path.basename(self.caminho_icone)}")

        # Refresh placeholder text if still showing
        if self._args_placeholder_active:
            self.entry_args.delete(0, tk.END)
            self.entry_args.insert(0, t["args_placeholder"])

        # Refresh category label and dropdown
        self.lbl_cat.config(text=t["cat_label"])
        self._refresh_cat_menu()

    # ── Path persistence ──────────────────────────────────────────────────────
    def get_last_path(self):
        try:
            path = self._load_settings().get("last_path", "")
            if path and os.path.isdir(path):
                return path
        except Exception:
            pass
        default_start = Path("/mnt")
        return str(default_start) if default_start.exists() else str(Path.home())

    def save_last_path(self, path):
        self._save_settings(last_path=path)

    # ── File selection ────────────────────────────────────────────────────────
    def _detectar_tipo(self, caminho):
        """Return 'wine' (Windows PE), 'appimage' or 'native'.

        Detection order:
        1. .exe extension              → wine
        2. MZ magic bytes (PE header)  → wine
        3. .sh extension               → native
        4. Shebang (#!) first line     → native  (sh, bash, python, ruby, node, perl…)
        5. ELF + AppImage magic ('AI' 0x01/0x02 at offset 8, or *.AppImage) → appimage
        6. ELF magic bytes (7f 45 4c 46) → native
        7. Fallback                    → native
        """
        lower = caminho.lower()

        if lower.endswith(".exe"):
            return "wine"

        try:
            with open(caminho, "rb") as f:
                header = f.read(16)
        except OSError:
            return "native"

        if header[:2] == b"MZ":
            return "wine"
        if lower.endswith(".sh"):
            return "native"
        if header[:2] == b"#!":
            return "native"
        if header[:4] == b"\x7fELF":
            return "appimage" if eh_appimage(header, lower) else "native"

        return "native"

    def _aplicar_tipo(self, tipo):
        """Set the radio button and show the detection result in the step label."""
        self.exe_type.set(tipo)
        t = self.texts[self.lang]
        self.lbl_step1.config(
            text=t[self._step1_key()],
            fg={"wine": self.color_blue, "appimage": self.color_green}.get(tipo, self.color_purple)
        )

    def selecionar_exe(self):
        t = self.texts[self.lang]

        caminho = self.modern_file_picker(
            title=t.get("ask_exe", "Select executable"),
            initialdir=self.get_last_path(),
            filetypes=[
                ("All files", "*"),
                ("Executables", "*.exe *.sh *.bin *.run *.AppImage *.appimage *.elf"),
                ("Shell scripts", "*.sh"),
                ("Windows executables", "*.exe"),
            ]
        )

        if caminho:
            escolhido = caminho
            # Resolve symlinks right away. A link kept on the Desktop (or in any other
            # folder) must never be mistaken for the program's real location, or the
            # shortcut's working directory (Path=) would point there and the program
            # would drop its files in that folder.
            caminho = os.path.realpath(caminho)
            self.caminho_exe = caminho
            self._icone_appimage = None
            self.save_last_path(os.path.dirname(escolhido))
            self.lbl_exe.config(text=os.path.basename(caminho), fg=self.fg_color)

            nome_base = os.path.splitext(os.path.basename(escolhido))[0].replace("_", " ").replace("-", " ").title()
            self.entry_nome.delete(0, tk.END)
            self.entry_nome.insert(0, nome_base)

            # Auto-detect type and update radio buttons
            tipo_detectado = self._detectar_tipo(caminho)
            self._aplicar_tipo(tipo_detectado)
            # Lock .sh to native so manual override via radio can't break Exec line
            if caminho.lower().endswith(".sh"):
                tipo_detectado = "native"
                self._aplicar_tipo("native")

            badge = {"wine": "  [Windows/Wine]", "appimage": "  [AppImage]"}.get(tipo_detectado, "  [Linux native]")
            badge_color = {"wine": self.color_blue, "appimage": self.color_green}.get(tipo_detectado, self.color_purple)
            self.lbl_exe.config(
                text=os.path.basename(caminho) + badge,
                fg=badge_color
            )

            if tipo_detectado == "wine":
                self.extrair_icone_automatico()
            elif tipo_detectado == "appimage":
                self.extrair_icone_appimage()
            else:
                self.buscar_icone_nativo(os.path.basename(caminho))

    # ── Icon extraction: Wine .exe ────────────────────────────────────────────
    def extrair_icone_automatico(self):
        self.lbl_icone.config(text=self.texts[self.lang]["extracting"], fg=self.color_orange)
        self.root.update()

        pasta_icones = Path.home() / ".local" / "share" / "icons" / "wine_linux_shortcut_maker"
        pasta_icones.mkdir(parents=True, exist_ok=True)

        nome_limpo = "".join(x for x in self.entry_nome.get() if x.isalnum()) or "icone"
        caminho_saida = pasta_icones / f"{nome_limpo}.ico"

        comando = f'wrestool -x -t 14 "{self.caminho_exe}" > "{caminho_saida}"'
        resultado = subprocess.run(comando, shell=True, stderr=subprocess.DEVNULL)

        if resultado.returncode == 0 and caminho_saida.exists() and caminho_saida.stat().st_size > 0:
            self.caminho_icone = str(caminho_saida)
            self.status_icone  = "success"
            self.lbl_icone.config(text=self.texts[self.lang]["ext_success"], fg=self.color_green)
        else:
            self.caminho_icone = "wine"
            self.status_icone  = "fail"
            self.lbl_icone.config(text=self.texts[self.lang]["ext_fail"], fg=self.color_red)
            if caminho_saida.exists():
                caminho_saida.unlink()

    # ── Icon lookup: native Linux binary ─────────────────────────────────────
    def buscar_icone_nativo(self, nome_binario):
        """Heuristic: check common icon dirs for a file matching the binary name."""
        nome_lower = os.path.splitext(nome_binario)[0].lower()
        search_dirs = [
            "/usr/share/icons/hicolor/256x256/apps",
            "/usr/share/icons/hicolor/128x128/apps",
            "/usr/share/icons/hicolor/64x64/apps",
            "/usr/share/icons/hicolor/48x48/apps",
            "/usr/share/pixmaps",
            str(Path.home() / ".local" / "share" / "icons"),
        ]
        for d in search_dirs:
            p = Path(d)
            if not p.exists():
                continue
            for f in p.iterdir():
                if nome_lower in f.name.lower() and f.suffix.lower() in (".png", ".svg", ".xpm", ".ico"):
                    self.caminho_icone = str(f)
                    self.status_icone  = "success"
                    self.lbl_icone.config(
                        text=f"{self.texts[self.lang]['custom_icon']}{f.name}",
                        fg=self.color_green
                    )
                    return
        self.caminho_icone = ""
        self.status_icone  = "default"
        self.lbl_icone.config(
            text=self.texts[self.lang]["default_icon_native"],
            fg=self.color_gray
        )

    # ── Icon: AppImage ───────────────────────────────────────────────────────
    @staticmethod
    def _garantir_executavel(caminho):
        """An AppImage has to be executable to launch (and to read its own icon)."""
        try:
            if not os.access(caminho, os.X_OK):
                os.chmod(caminho, os.stat(caminho).st_mode | 0o111)
        except OSError:
            pass

    def extrair_icone_appimage(self):
        """Read the name and icon straight from the AppImage.

        Nothing is written to disk here. The icon stays in memory until the
        shortcut is created, and is not written at all when an icon with the
        same name is already installed on the system.
        """
        t = self.texts[self.lang]
        self.lbl_icone.config(text=t["extracting"], fg=self.color_orange)
        self.root.update()

        self._garantir_executavel(self.caminho_exe)
        info = extrair_dados_appimage(self.caminho_exe)

        if info["nome"]:
            self.entry_nome.delete(0, tk.END)
            self.entry_nome.insert(0, info["nome"])

        if info["icone_instalado"]:
            self.caminho_icone = info["icone_nome"]
            self.status_icone  = "reused"
            self.lbl_icone.config(text=t["icon_reused"].format(info["icone_nome"]), fg=self.color_green)
        elif info["icone_dados"]:
            self._icone_appimage = (info["icone_dados"], info["icone_ext"])
            self.caminho_icone   = ""
            self.status_icone    = "success"
            self.lbl_icone.config(text=t["ext_success_appimage"], fg=self.color_green)
        else:
            self.buscar_icone_nativo(os.path.basename(self.caminho_exe))

    def _gravar_icone_appimage(self, nome_arquivo_seguro):
        """Save the in-memory AppImage icon (only called when the shortcut is created)."""
        dados, ext = self._icone_appimage
        APPIMAGE_ICON_DIR.mkdir(parents=True, exist_ok=True)
        destino = APPIMAGE_ICON_DIR / f"{nome_arquivo_seguro or 'appimage'}{ext}"
        destino.write_bytes(dados)
        return str(destino)

    # ── Manual icon picker ────────────────────────────────────────────────────
    def selecionar_icone_manual(self):
        caminho = self.modern_file_picker(
            title=self.texts[self.lang]["ask_icon"],
            initialdir=self.get_last_path(),
            filetypes=[("Images", "*.png *.ico *.svg *.jpg *.xpm")]
        )
        if caminho:
            self.caminho_icone = caminho
            self.status_icone  = "custom"
            self.lbl_icone.config(
                text=f"{self.texts[self.lang]['custom_icon']}{os.path.basename(caminho)}",
                fg=self.color_blue
            )

    # ── Modern embedded file picker ──────────────────────────────────────────
    def modern_file_picker(self, title="Select file", initialdir=None, filetypes=None):
        """Use native system file picker for modern UI.

        Priority: kdialog (KDE/Big Linux) -> zenity (GNOME) -> tkinter fallback.
        kdialog is tried first because on KDE sessions zenity (a GTK app) can
        randomly close or fail mid-session, causing the dialog to vanish.

        Returns the selected filepath string or empty string on cancel.
        """
        initialdir = initialdir or str(Path.home())
        filetypes = filetypes or [("All files", "*")]

        result = self._try_kdialog_picker(title, initialdir, filetypes)
        if result is not None:
            return result

        result = self._try_zenity_picker(title, initialdir, filetypes)
        if result is not None:
            return result

        return filedialog.askopenfilename(
            title=title,
            initialdir=initialdir,
            filetypes=filetypes
        )

    def _try_zenity_picker(self, title, initialdir, filetypes):
        """Try to use zenity (GNOME file picker).

        Returns: filepath string if successful, "" if cancelled, None if unavailable
        """
        try:
            if subprocess.run(["which", "zenity"], capture_output=True).returncode != 0:
                return None

            filters = []
            for label, pattern in filetypes:
                patterns = pattern.split()
                filter_str = " ".join(patterns)
                filters.extend(["--file-filter", f"{label} | {filter_str}"])

            cmd = ["zenity", "--file-selection", "--title", title,
                   "--filename", str(initialdir) + "/"] + filters

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return ""
        except Exception:
            return None

    def _try_kdialog_picker(self, title, initialdir, filetypes):
        """Try to use kdialog (KDE file picker).

        Returns: filepath string if successful, "" if cancelled, None if unavailable
        """
        try:
            if subprocess.run(["which", "kdialog"], capture_output=True).returncode != 0:
                return None

            # kdialog does not understand several "Label (patterns)" entries glued
            # into one string (it can end up listing only the last pattern, hiding
            # e.g. .AppImage files). When "All files" is the first entry, which is
            # the default anyway, just don't pass a filter at all.
            if filetypes and filetypes[0][1].strip() == "*":
                filters = ""
            else:
                filters = ""
                for label, pattern in filetypes:
                    patterns = pattern.split()
                    filter_str = " ".join(patterns)
                    filters += f"{label} ({filter_str}) "

            cmd = ["kdialog", "--getopenfilename", str(initialdir)]
            if filters:
                cmd.append(filters)
            cmd += ["--title", title]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return ""
        except Exception:
            return None

    # ── Category dropdown callback ────────────────────────────────────────────
    def _on_cat_change(self, selected_label):
        """Map the displayed label back to the XDG key stored in self.category."""
        for key, lbl in self.texts[self.lang]["categories"]:
            if lbl == selected_label:
                self.category.set(key)
                self._save_settings()
                break

    def _refresh_cat_menu(self):
        """Rebuild the OptionMenu entries for the current language."""
        cats = self.texts[self.lang]["categories"]
        self._cat_keys   = [k for k, _ in cats]
        self._cat_labels = [lbl for _, lbl in cats]

        current_key = self.category.get()
        new_label = self._cat_labels[0]
        for key, lbl in cats:
            if key == current_key:
                new_label = lbl
                break
        self._cat_display.set(new_label)

        menu = self.opt_cat["menu"]
        menu.delete(0, "end")
        for lbl in self._cat_labels:
            menu.add_command(label=lbl,
                             command=lambda l=lbl: (self._cat_display.set(l),
                                                    self._on_cat_change(l)))

    # ── Create shortcut ───────────────────────────────────────────────────────
    def criar_atalho(self):
        t = self.texts[self.lang]
        is_wine = self.exe_type.get() == "wine"
        is_appimage = self.exe_type.get() == "appimage"

        if not self.caminho_exe:
            messagebox.showwarning("Atenção / Warning", t["err_step1"])
            return

        nome_atalho = self.entry_nome.get().strip()
        if not nome_atalho:
            messagebox.showwarning("Atenção / Warning", t["err_empty_name"])
            return

        extra_args = self._get_args()
        # Working directory of the launcher. caminho_exe is already symlink-resolved,
        # so this is the program's real folder, never the Desktop where a link or
        # the shortcut itself may live.
        pasta_trabalho = os.path.dirname(self.caminho_exe)
        pasta_desktop  = self.obter_area_de_trabalho()
        # ...except an AppImage that physically sits on the Desktop: don't make the
        # Desktop its working folder, start it from the home folder instead.
        if is_appimage and os.path.realpath(pasta_trabalho) == os.path.realpath(pasta_desktop):
            pasta_trabalho = str(Path.home())
        pasta_menu     = Path.home() / ".local" / "share" / "applications"

        nome_arquivo_seguro = (
            "".join(x for x in nome_atalho if x.isalnum() or x in " -_")
            .strip().replace(" ", "_").lower()
        )

        is_shell_script = self.caminho_exe.lower().endswith(".sh")
        if is_wine and not is_shell_script:
            args_part = f' "{extra_args}"' if extra_args else ""
            exec_cmd  = f'sh -c "cd \\"{pasta_trabalho}\\" && wine \\"{self.caminho_exe}\\"{args_part} > /dev/null 2>&1"'
            prefix    = "wine_"
        else:
            args_part = f" {extra_args}" if extra_args else ""
            programa = f'sh "{self.caminho_exe}"' if is_shell_script else f'"{self.caminho_exe}"'
            # `env -C` changes directory before starting the program. Path= alone is
            # not honoured by every launcher, and when it isn't, the program starts
            # in the folder the shortcut was launched from (e.g. the Desktop).
            exec_cmd = f'env -C "{pasta_trabalho}" {programa}{args_part}'
            prefix    = "appimage_" if is_appimage else "native_"

        icon_value = self.caminho_icone if self.caminho_icone else "application-x-executable"
        if is_appimage and self.status_icone == "success" and self._icone_appimage:
            try:
                icon_value = self._gravar_icone_appimage(nome_arquivo_seguro)
            except OSError:
                pass  # keep the generic icon

        xdg_cat = self.category.get()
        if is_wine and not is_shell_script:
            categories_line = f"Wine;{xdg_cat};Application;"
        else:
            categories_line = f"{xdg_cat};Application;"

        conteudo_desktop = (
            "[Desktop Entry]\n"
            f"Name={nome_atalho}\n"
            "Type=Application\n"
            f"Exec={exec_cmd}\n"
            f"Path={pasta_trabalho}\n"
            f"Icon={icon_value}\n"
            "Terminal=false\n"
            f"Categories={categories_line}\n"
        )

        arquivo_desktop = pasta_desktop / f"{nome_arquivo_seguro}.desktop"
        arquivo_menu    = pasta_menu    / f"{prefix}{nome_arquivo_seguro}.desktop"

        try:
            pasta_menu.mkdir(parents=True, exist_ok=True)
            pasta_desktop.mkdir(parents=True, exist_ok=True)

            for destino in (arquivo_desktop, arquivo_menu):
                with open(destino, 'w', encoding='utf-8') as f:
                    f.write(conteudo_desktop)
                os.chmod(destino, 0o755)

            if arquivo_desktop.exists():
                subprocess.run(
                    ['gio', 'set', str(arquivo_desktop), 'metadata::trusted', 'true'],
                    stderr=subprocess.DEVNULL
                )

            subprocess.run(
                ['update-desktop-database', str(pasta_menu)],
                stderr=subprocess.DEVNULL
            )

            msg_key = "success_msg_wine" if is_wine else "success_msg_appimage" if is_appimage else "success_msg_native"
            messagebox.showinfo(t["success_title"], t[msg_key].format(nome_atalho))

        except Exception as e:
            messagebox.showerror(t["err_title"], t["err_msg"].format(e))

    # ── Desktop path helper ───────────────────────────────────────────────────
    def obter_area_de_trabalho(self):
        try:
            res = subprocess.run(['xdg-user-dir', 'DESKTOP'],
                                 stdout=subprocess.PIPE, text=True)
            return Path(res.stdout.strip())
        except Exception:
            return Path.home() / "Desktop"


if __name__ == "__main__":
    root = tk.Tk()
    app = LinuxShortcutMaker(root)
    root.mainloop()
