#!/usr/bin/env bash
# =====================================================================
#  install.sh — instalador da Jester (Termux e Debian/Ubuntu)
# =====================================================================
#  - Essencial (sempre instalado): python3, pip, requests, bs4, lxml.
#  - Opcional (aceleradores — use --full para instalar tudo de uma vez,
#    ou responda "s" quando perguntado): golang, g++/clang, php, nodejs.
#    Se algum deles faltar, a Jester continua funcionando sem ele —
#    ela nunca depende de um acelerador pra clonar um site.
# =====================================================================

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
TOOLS="$SCRIPT_DIR/tools"
MODO_FULL=0
[ "${1:-}" = "--full" ] && MODO_FULL=1

echo "=================================================================="
echo " Jester — instalador de dependências"
echo "=================================================================="
echo

# --------------------------------------------------------- detectar ambiente
IS_TERMUX=0
if [ -n "${TERMUX_VERSION:-}" ] || command -v pkg >/dev/null 2>&1; then
    IS_TERMUX=1
fi

if [ "$IS_TERMUX" -eq 1 ]; then
    echo "[install] Ambiente detectado: Termux"
    GERENCIADOR="pkg"
    PKG_PYTHON="python"
    PKG_GO="golang"
    PKG_CPP="clang"
    PKG_PHP="php"
    PKG_NODE="nodejs"
elif command -v apt-get >/dev/null 2>&1; then
    echo "[install] Ambiente detectado: Debian/Ubuntu (apt)"
    GERENCIADOR="apt-get"
    PKG_PYTHON="python3 python3-pip"
    PKG_GO="golang-go"
    PKG_CPP="g++"
    PKG_PHP="php-cli"
    PKG_NODE="nodejs"
else
    echo "[install] Não achei 'pkg' (Termux) nem 'apt-get' (Debian/Ubuntu)."
    echo "          Instale manualmente: python3, pip3, g++, php-cli, nodejs, golang"
    echo "          e depois rode este script de novo (ele vai compilar os"
    echo "          aceleradores se achar os compiladores já instalados)."
    GERENCIADOR=""
fi

instalar() {
    # instalar <pacotes...> — nunca derruba o script se um pacote falhar
    if [ -z "$GERENCIADOR" ]; then return 1; fi
    if [ "$GERENCIADOR" = "pkg" ]; then
        pkg install -y "$@"
    else
        sudo apt-get update -qq 2>/dev/null
        sudo apt-get install -y "$@"
    fi
}

# --------------------------------------------------------- essencial: python
echo
echo "[install] Instalando base Python (essencial)..."
if ! command -v python3 >/dev/null 2>&1; then
    instalar $PKG_PYTHON || echo "[install] AVISO: não consegui instalar o Python automaticamente."
fi

if command -v pip3 >/dev/null 2>&1 || python3 -m pip --version >/dev/null 2>&1; then
    echo "[install] Instalando requests, beautifulsoup4, lxml via pip..."
    python3 -m pip install --quiet --break-system-packages requests beautifulsoup4 lxml 2>/dev/null \
        || python3 -m pip install --quiet requests beautifulsoup4 lxml 2>/dev/null \
        || echo "[install] AVISO: pip falhou. Tentando pacotes do sistema..."
fi

python3 -c "import requests, bs4, lxml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[install] Tentando requests/bs4/lxml como pacotes do sistema..."
    if [ "$IS_TERMUX" -eq 1 ]; then
        instalar python-requests python-lxml 2>/dev/null
        python3 -m pip install --quiet --break-system-packages beautifulsoup4 2>/dev/null
    else
        instalar python3-requests python3-bs4 python3-lxml 2>/dev/null
    fi
fi

python3 -c "import requests, bs4, lxml" 2>/dev/null \
    && echo "[install] Python OK (requests, bs4, lxml)." \
    || echo "[install] ATENÇÃO: não confirmei requests/bs4/lxml — a Jester pode não rodar."

# --------------------------------------------------------- aceleradores opcionais
instalar_turbo=0
if [ "$MODO_FULL" -eq 1 ]; then
    instalar_turbo=1
else
    echo
    read -r -p "[install] Instalar também os aceleradores opcionais (Go, C++, PHP, Node)? [S/n]: " RESP
    case "$RESP" in
        n|N|nao|não|NAO|NÃO) instalar_turbo=0 ;;
        *) instalar_turbo=1 ;;
    esac
fi

if [ "$instalar_turbo" -eq 1 ]; then
    echo
    echo "[install] Instalando Go (acelerador de download + sitemap)..."
    command -v go >/dev/null 2>&1 || instalar $PKG_GO

    echo "[install] Instalando compilador C++ (checagem de integridade)..."
    command -v g++ >/dev/null 2>&1 || command -v clang++ >/dev/null 2>&1 || instalar $PKG_CPP

    echo "[install] Instalando PHP (preview local do clone)..."
    command -v php >/dev/null 2>&1 || instalar $PKG_PHP

    echo "[install] Instalando Node.js (varredura extra de JS)..."
    command -v node >/dev/null 2>&1 || instalar $PKG_NODE
else
    echo "[install] Pulando aceleradores opcionais — a Jester funciona só com Python."
fi

# --------------------------------------------------------- compilar os aceleradores
echo
echo "[install] Compilando aceleradores disponíveis..."

if command -v go >/dev/null 2>&1; then
    if (cd "$TOOLS" && go build -o fastfetch fastfetch.go) 2>/tmp/jester_go_err.log; then
        chmod +x "$TOOLS/fastfetch"
        echo "[install]   -> fastfetch (Go) compilado com sucesso."
    else
        echo "[install]   -> falha ao compilar fastfetch.go (veja /tmp/jester_go_err.log). Seguindo sem ele."
    fi
else
    echo "[install]   -> Go não encontrado: pulando fastfetch (a Jester funciona sem ele)."
fi

CXX=""
command -v g++ >/dev/null 2>&1 && CXX="g++"
[ -z "$CXX" ] && command -v clang++ >/dev/null 2>&1 && CXX="clang++"
if [ -n "$CXX" ]; then
    if (cd "$TOOLS" && "$CXX" -std=c++17 -O2 -o checksum checksum.cpp) 2>/tmp/jester_cpp_err.log; then
        chmod +x "$TOOLS/checksum"
        echo "[install]   -> checksum (C++, $CXX) compilado com sucesso."
    else
        echo "[install]   -> falha ao compilar checksum.cpp (veja /tmp/jester_cpp_err.log). Seguindo sem ele."
    fi
else
    echo "[install]   -> g++/clang++ não encontrado: pulando checksum (opcional)."
fi

if command -v php >/dev/null 2>&1; then
    echo "[install]   -> PHP disponível (preview local habilitado)."
else
    echo "[install]   -> PHP não encontrado: preview local ficará indisponível (opcional)."
fi

if command -v node >/dev/null 2>&1; then
    echo "[install]   -> Node.js disponível (extração extra de links em JS habilitada)."
else
    echo "[install]   -> Node.js não encontrado: a Jester usa só o regex em Python (sem perda essencial)."
fi

chmod +x "$SCRIPT_DIR/jester.sh" 2>/dev/null

echo
echo "=================================================================="
echo " Instalação concluída. Para usar:"
echo "   ./jester.sh exemplo.com"
echo "=================================================================="
