# Linux Shortcut Maker Z 🚀

O **Linux Shortcut Maker Z** é uma ferramenta de interface gráfica (GUI) simples e leve, desenvolvida em Python (Tkinter), projetada especificamente para usuários de Linux (como BigLinux, Ubuntu, Fedora, etc.) que utilizam o **Wine** para rodar aplicativos e jogos do Windows (`.exe`).

## 📋 O Problema que ele resolve

Criar links simbólicos diretamente para um arquivo `.exe` na Área de Trabalho do Linux costuma quebrar o programa. Isso ocorre porque o Wine exige que a **Pasta de Trabalho** (*Working Directory*) seja exatamente a pasta onde o executável original e suas respectivas `.dll` estão contidos. Se você rodar apenas o link, o aplicativo tenta carregar na Área de Trabalho e falha.

**A Solução Z:** Este programa automatiza a criação de um lançador `.desktop` nativo do Linux. Você só precisa selecionar o arquivo `.exe` e o programa deduz a pasta de trabalho, monta o comando correto do Wine, aplica as permissões de execução (`chmod +x`) e envia o atalho pronto para a sua Área de Trabalho com apenas um clique.

## ✨ Funcionalidades

- 🗔 **Interface Gráfica Intuitiva:** Sem necessidade de usar o terminal para criar atalhos.
- 📂 **Detecção Automática de Caminho:** Identifica a pasta raiz do arquivo `.exe` instantaneamente.
- 💻 **Instalador Inteligente (`build.sh`):** Compila o programa na pasta local e cria um atalho nativo diretamente no seu Menu Iniciar do sistema.
- 🛠️ **Independente de Case-Sensitivity:** O script de build reconhece o código tanto em maiúsculo quanto em minúsculo.

## 🛠️ Pré-requisitos

O programa utiliza dependências nativas que geralmente já vêm instaladas no BigLinux e em outras distribuições com KDE Plasma:

```bash
# Python 3 e Tkinter (Interface Gráfica)
# No BigLinux/Manjaro/Arch:
sudo pacman -S python python-tkinter

# No Ubuntu/Debian/Mint:
sudo apt install python3 python3-tk