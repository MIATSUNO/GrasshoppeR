#!/usr/bin/env bash
# GrasshoppeR Suite — instalador unificado de dependências
# Suporta Termux e Debian/Ubuntu.
# Uso: bash install.sh
#      bash install.sh --no-python
#      bash install.sh --no-build

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="$ROOT/tools"
NO_PYTHON=0
NO_BUILD=0

for arg in "$@"; do
  case "$arg" in
    --no-python) NO_PYTHON=1 ;;
    --no-build)  NO_BUILD=1 ;;
    -h|--help)
      echo "Uso: bash install.sh [--no-python] [--no-build]"
      exit 0
      ;;
    *) echo "[ERRO] Opção desconhecida: $arg"; exit 2 ;;
  esac
done

log()  { printf '\n\033[1;36m[GrasshoppeR]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[AVISO]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[ERRO]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -d "$TOOLS" ]] || die "Pasta tools/ não encontrada. Coloque install.sh na raiz da Grasshopper-Suite."

OS_KIND=""
if [[ -n "${TERMUX_VERSION:-}" ]] || command -v pkg >/dev/null 2>&1; then
  OS_KIND="termux"
elif command -v apt-get >/dev/null 2>&1; then
  OS_KIND="apt"
else
  die "Sistema não suportado automaticamente. Este instalador atende Termux e Debian/Ubuntu."
fi

as_root() {
  if [[ "$OS_KIND" == "termux" ]]; then
    "$@"
  elif [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    die "É necessário root ou sudo para instalar pacotes do sistema."
  fi
}

install_system() {
  if [[ "$OS_KIND" == "termux" ]]; then
    pkg install -y "$@"
  else
    as_root apt-get install -y "$@"
  fi
}

log "Atualizando índices de pacotes..."
if [[ "$OS_KIND" == "termux" ]]; then
  pkg update -y
else
  as_root apt-get update
fi

if [[ "$OS_KIND" == "termux" ]]; then
  # Base, compilação dos programas Go/C++, interpretadores e utilitários
  # usados por Mianba/Jester.
  SYSTEM_PACKAGES=(
    python clang golang php nodejs
    traceroute dnsutils whois iproute2
    coreutils findutils
  )
else
  SYSTEM_PACKAGES=(
    python3 python3-pip python3-venv
    build-essential golang-go php-cli nodejs npm
    traceroute dnsutils whois iproute2
    ca-certificates curl git
    coreutils findutils
    python3-requests python3-bs4 python3-rich python3-colorama
  )
fi

log "Instalando runtimes, compiladores e utilitários..."
install_system "${SYSTEM_PACKAGES[@]}"

PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$candidate")"
    break
  fi
done
[[ -n "$PYTHON_BIN" ]] || die "Python não foi encontrado após a instalação."

log "Python detectado: $("$PYTHON_BIN" --version 2>&1)"
log "Go: $(go version 2>/dev/null || echo indisponível)"
log "Node: $(node --version 2>/dev/null || echo indisponível)"
log "PHP: $(php --version 2>/dev/null | head -n1 || echo indisponível)"

if [[ "$NO_PYTHON" -eq 0 ]]; then
  REQ="$ROOT/requests.txt"
  [[ -f "$REQ" ]] || die "requests.txt não encontrado na raiz do projeto."

  log "Instalando bibliotecas Python listadas em requests.txt..."
  # O Termux normalmente permite pip no ambiente do próprio app.
  # Em Debian/Ubuntu, tenta primeiro o ambiente do sistema; se PEP 668
  # bloquear, usa um venv local para não quebrar o Python do sistema.
  if "$PYTHON_BIN" -m pip install -r "$REQ"; then
    :
  elif "$PYTHON_BIN" -m pip install --break-system-packages -r "$REQ"; then
    :
  else
    log "Pip global indisponível; criando ambiente virtual .venv..."
    "$PYTHON_BIN" -m venv "$ROOT/.venv" || die "Não foi possível criar .venv."
    "$ROOT/.venv/bin/python" -m pip install --upgrade pip
    "$ROOT/.venv/bin/python" -m pip install -r "$REQ"
    warn "Bibliotecas instaladas em .venv. Para executar a suíte usando-as:"
    echo "  source \"$ROOT/.venv/bin/activate\""
  fi
fi

if [[ "$NO_BUILD" -eq 0 ]]; then
  log "Compilando ferramentas Go disponíveis..."

  if command -v go >/dev/null 2>&1; then
    if [[ -f "$TOOLS/moonscan.go" ]]; then
      (cd "$TOOLS" && go build -o moonscan moonscan.go) \
        && chmod +x "$TOOLS/moonscan" \
        && log "MoonScan compilado: tools/moonscan" \
        || warn "Falha ao compilar MoonScan; consulte a mensagem do Go."
    fi

    if [[ -f "$TOOLS/tools/fastfetch.go" ]]; then
      (cd "$TOOLS" && go build -o fastfetch ./tools/fastfetch.go) \
        && chmod +x "$TOOLS/fastfetch" \
        && log "FastFetch da Jester compilado: tools/fastfetch" \
        || warn "Falha ao compilar FastFetch."
    fi
  else
    warn "Go indisponível; binários Go não foram compilados."
  fi

  log "Compilando utilitário C++ checksum..."
  CXX=""
  command -v clang++ >/dev/null 2>&1 && CXX="clang++"
  command -v g++ >/dev/null 2>&1 && CXX="g++"
  if [[ -n "$CXX" && -f "$TOOLS/tools/checksum.cpp" ]]; then
    (cd "$TOOLS" && "$CXX" -std=c++17 -O2 -Wall -Wextra -o checksum tools/checksum.cpp) \
      && chmod +x "$TOOLS/checksum" \
      && log "Checksum compilado: tools/checksum" \
      || warn "Falha ao compilar checksum."
  else
    warn "Compilador C++ indisponível; checksum não foi compilado."
  fi
fi

# Permissões dos scripts distribuídos.
chmod +x "$TOOLS/jester.sh" 2>/dev/null || true
chmod +x "$TOOLS/install.sh" 2>/dev/null || true

log "Verificando bibliotecas Python principais..."
"$PYTHON_BIN" - <<'PY' || warn "Uma ou mais bibliotecas Python não estão disponíveis no Python global."
modules = ("requests", "bs4", "rich", "colorama")
missing = []
for module in modules:
    try:
        __import__(module)
        print(f"  [OK] {module}")
    except ImportError:
        print(f"  [FALTA] {module}")
        missing.append(module)
if missing:
    raise SystemExit(1)
PY

cat <<'EOF'

============================================================
 GrasshoppeR Suite — instalação finalizada
============================================================
Dependências Python: requests.txt
Shell/Jester: bash tools/jester.sh
Launcher:     python3 Grasshopper.py

Utilitários opcionais do módulo de pentest não são instalados
por este script. Instale e utilize ferramentas de auditoria
separadamente, somente em sistemas e redes com autorização.
============================================================
EOF
