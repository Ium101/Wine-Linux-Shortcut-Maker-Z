# Wine Linux Shortcut Maker Z 🚀

🌍 **Choose your language / Escolha seu idioma:**
- [🇺🇸 Read in English](#-english-version)
- [🇧🇷 Ler em Português (PT-BR)](#-versão-em-português-pt-br)

---

## 🇺🇸 English Version

**Wine Linux Shortcut Maker Z** is a simple and lightweight graphical user interface (GUI) tool developed in Python (Tkinter), specifically designed for Linux users (such as BigLinux, Ubuntu, Fedora, etc.) who use **Wine** to run Windows applications and games (`.exe`).

### 📋 The Problem it Solves

Creating symbolic links directly to an `.exe` file on the Linux Desktop usually breaks the program. This happens because Wine requires the **Working Directory** to be exactly the folder where the original executable and its respective `.dll` files are located. If you run just the link, the application tries to load on the Desktop and fails.

**The Z Solution:** This program automates the creation of a native Linux `.desktop` launcher. You only need to select the `.exe` file, and the program deduces the working directory, assembles the correct Wine command, applies execution permissions (`chmod +x`), and sends the ready-made shortcut to your Desktop with just one click.

### ✨ Features

- 🗔 **Intuitive Graphical Interface:** No need to use the terminal to create shortcuts.
- 📂 **Automatic Path Detection:** Instantly identifies the root folder of the `.exe` file.
- 💻 **Smart Installer (`build.sh`):** Compiles the program in the local folder and creates a native shortcut directly in your system's Start Menu.
- 🛠️ **Case-Insensitive:** The build script recognizes code in both uppercase and lowercase.

### 🛠️ Prerequisites

The program uses native dependencies that usually come pre-installed in BigLinux and other distributions with KDE Plasma:

```bash
# On BigLinux / Manjaro / Arch:
sudo pacman -S python python-tkinter

# On Ubuntu / Debian / Mint:
sudo apt install python3 python3-tk
```

---

## 🇧🇷 Versão em Português (PT-BR)

**Wine Linux Shortcut Maker Z** é uma ferramenta de interface gráfica (GUI) simples e leve, desenvolvida em Python (Tkinter), especialmente projetada para usuários Linux (como BigLinux, Ubuntu, Fedora, etc.) que utilizam o **Wine** para executar aplicativos e jogos Windows (`.exe`).

### 📋 O Problema que Resolve

Criar links simbólicos diretamente para um arquivo `.exe` na Área de Trabalho do Linux geralmente quebra o programa. Isso acontece porque o Wine exige que o **Diretório de Trabalho** seja exatamente a pasta onde o executável original e seus respectivos arquivos `.dll` estão localizados. Se você executar apenas o link, o aplicativo tenta carregar a partir da Área de Trabalho e falha.

**A Solução Z:** Este programa automatiza a criação de um launcher nativo Linux `.desktop`. Você só precisa selecionar o arquivo `.exe`, e o programa deduz o diretório de trabalho, monta o comando Wine correto, aplica as permissões de execução (`chmod +x`) e envia o atalho pronto para sua Área de Trabalho com apenas um clique.

### ✨ Recursos

- 🗔 **Interface Gráfica Intuitiva:** Sem necessidade de usar o terminal para criar atalhos.
- 📂 **Detecção Automática de Caminho:** Identifica instantaneamente a pasta raiz do arquivo `.exe`.
- 💻 **Instalador Inteligente (`build.sh`):** Compila o programa na pasta local e cria um atalho nativo diretamente no Menu Iniciar do seu sistema.
- 🛠️ **Sem Distinção de Maiúsculas/Minúsculas:** O script de build reconhece o código tanto em letras maiúsculas quanto minúsculas.

### 🛠️ Pré-requisitos

O programa utiliza dependências nativas que geralmente vêm pré-instaladas no BigLinux e em outras distribuições com KDE Plasma:

```bash
# No BigLinux / Manjaro / Arch:
sudo pacman -S python python-tkinter

# No Ubuntu / Debian / Mint:
sudo apt install python3 python3-tk
```
