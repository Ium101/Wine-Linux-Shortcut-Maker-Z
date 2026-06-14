# Linux Shortcut Maker Z 🚀

🌍 **English Version** | 🇧🇷 **Versão em Português**

---

## 🌍 English Version

**Linux Shortcut Maker Z** is a simple and lightweight graphical user interface (GUI) tool developed in Python (Tkinter), specifically designed for Linux users (such as BigLinux, Ubuntu, Fedora, etc.) who use **Wine** to run Windows applications and games (`.exe`).

### 📋 The Problem it Solves

Creating symbolic links directly to an `.exe` file on the Linux Desktop usually breaks the program. This happens because Wine requires the **Working Directory** to be exactly the folder where the original executable and its respective `.dll` files are located. If you run just the link, the application tries to load on the Desktop and fails.

**The Z Solution:** This program automates the creation of a native Linux `.desktop` launcher. You only need to select the `.exe` file, and the program deduces the working directory, assembles the correct Wine command, applies execution permissions (`chmod +x`), and sends the ready-made shortcut to your Desktop with just one click.

### ✨ Features

*   🗔 **Intuitive Graphical Interface:** No need to use the terminal to create shortcuts.
*   📂 **Automatic Path Detection:** Instantly identifies the root folder of the `.exe` file.
*   💻 **Smart Installer (`build.sh`):** Compiles the program in the local folder and creates a native shortcut directly in your system's Start Menu.
*   🛠️ **Case-Insensitive:** The build script recognizes code in both uppercase and lowercase.

### 🛠️ Prerequisites

The program uses native dependencies that usually come pre-installed in BigLinux and other distributions with KDE Plasma:

```bash
# Python 3 and Tkinter (Graphical Interface)[cite: 1]
# On BigLinux/Manjaro/Arch[cite: 1]:
sudo pacman -S python python-tkinter

# On Ubuntu/Debian/Mint[cite: 1]:
sudo apt install python3 python3-tk