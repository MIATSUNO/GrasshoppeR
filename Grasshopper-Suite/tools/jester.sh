#!/usr/bin/env bash

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
CORE="$SCRIPT_DIR/core/jestercopy.py"
TOOLS="$SCRIPT_DIR/tools"

COR_RESET=""; COR_TITULO=""; COR_AVISO=""; COR_OK=""
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
    COR_RESET="$(tput sgr0)"
    COR_TITULO="$(tput setaf 6)$(tput bold)"   # ciano
    COR_AVISO="$(tput setaf 3)$(tput bold)"    # amarelo
    COR_OK="$(tput setaf 2)"                   # verde
fi

mostrar_banner() {
cat <<'BANNER_EOF'

[38;2;239;68;68m⠀⠀⠈⠈⠐⠈⠀⠁⠀⠈⠈⠀⠁⠈⠀⠈⠀⠁⠈⠀⠁⠁⠀⠈⠀⠈⠀⠀⠊⠈⠀⠁⠁⠈⠀⠀⠁⠁⠁⠁⠈⠈⠀⠁⠀⠀⠀⠀⠀⠀⢀⠆⠁⡠⠔⡅⡔⢄⠀⠄⠀⠀⠀⠀⠀⢀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⠔⡃⡍⢔⠨⡀⠄⠀⠀⠀⠀⠀⡐⠅⢀⠦⡃⡔⢜⠨⠢⢃⠈⠀⡠⠂⡪⠘⠀⠡⠀⢐⠨⠀⡂⠄⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡐⠠⠀⡀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⡔⡡⡐⠈⠀⢁⠪⠠⡂⠅⡀⠀⠂⡐⠀⢀⡢⠃⡜⠌⠐⠈⠈⡂⡂⡑⠌⠈⡀⠄⡂⠅⠌⡐⡨⠨⡠⠁⢆⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡂⠁⠀⡤⢌⠀⠢⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⡸⡸⠈⠀⠀⠐⠀⠀⠁⢌⠔⠐⡀⢀⠀⠀⡔⠡⠩⢈⢄⠀⠀⠀⠀⢅⠀⠀⡐⠀⠀⢐⠨⠀⠀⠈⠈⡂⠕⢐⢅⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡂⠀⢰⡗⢖⠄⠀⠁⠀⠀⡠⠀⠀⠁⠀⠀⠠⢀⠀⠀⠀⠀⡨⢀⠀⠀⠀⠀⠀⠀⠠⠐⠈⡐⢀⠁⠀⡘⠀⡡⡪⡡⠂⠔⡀⠀⠀⠀⠄⠂⠀⠀⠀⠀⠈⠀⠀⠀⡀⠀⠈⠐⡨⢂⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⡀⢀⠀⠀⠂⠄⡈⠊⢊⠂⠠⡁⢀⣢⢤⠶⢵⠚⡢⠆⡤⡀⠐⠀⠀⠸⡏⣂⠆⠀⠀⠀⠀⠀⠀⢃⢀⢂⠂⡠⣖⠢⠘⡇⠕⡐⠅⡂⡂⠅⠀⠀⠐⡀⠀⠀⢀⠀⡀⠂⠈⠀⠀⠈⠀⡀⠈⡪⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠂⠁⠀⠀⠀⠀⡀⠀⠀⠁⠐⠈⡤⡶⠛⢨⠃⠁⢘⡀⠄⠑⠈⠩⠱⢔⡀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⢂⠢⡂⡈⠣⠊⡨⡊⠌⡂⠅⢀⠂⠐⠀⠀⠀⠂⠀⠀⠠⠈⠀⠀⠀⠀⠀⠀⠀⠀⢀⠪⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⢀⠀⠂⠀⠀⡑⠈⠐⠐⠠⠀⠄⠀⠀⢂⣽⠝⠒⠢⡓⠒⠁⠡⡃⠁⠈⠨⠀⠡⠡⠱⡀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⠈⠆⠰⣔⢄⢢⠪⡐⠁⡄⣞⡮⠺⠰⡀⠀⠀⠀⠄⠈⠀⠀⠄⠀⠀⠀⠀⠀⠀⠀⠀⡈⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠄⠀⠀⠀⡂⠂⢕⠅⠀⠢⠈⠌⢀⡟⡜⠀⠀⢘⠀⠀⠀⠀⡂⠀⠀⢀⠥⡠⣁⢉⠫⡁⡉⠐⠐⠐⠠⠀⡀⠀⠀⠀⠈⠜⡑⡻⣔⡈⣔⢽⡫⡞⠀⠊⠕⢃⠅⠀⠀⠀⠡⢀⠈⠀⠀⠀⠀⠀⠀⠀⠠⢽⠪⢨⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⢀⠀⡂⠔⡢⢒⠨⠨⠀⡁⢰⡓⡓⠐⠁⠏⠈⠈⠈⠈⡍⠉⠁⠘⠔⠀⠀⠐⠈⠄⠐⠀⠐⠀⡀⠀⠀⠡⠀⠀⠀⠀⢣⠀⠓⢽⡪⢗⠋⠀⠄⠄⠀⣆⢕⠀⠠⠀⠄⠁⠀⢀⠀⢀⢀⠀⠀⠀⠀⠑⠒⠁⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⡐⠈⠀⠀⠐⠐⠐⠐⠠⠈⠀⠂⠸⡔⠅⠀⠀⠣⠀⠀⠀⠀⢒⠀⠀⠀⡃⠌⠠⠁⠄⠅⠠⠁⠀⠀⠀⢀⠠⠈⠀⠀⠀⠀⠀⢇⢁⠨⣵⢣⡤⣔⣤⡸⡽⢕⢕⠀⠈⠈⠀⠀⠄⠀⠀⢀⢀⡠⡠⠀⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠈⠠⠀⠀⠀⠀⠀⠀⠀⠀⠐⡨⢐⢹⡑⡑⠁⠙⡅⠁⠁⠁⡹⠈⠀⠀⠅⠄⠠⢀⢄⢂⣀⢀⡀⡂⠁⠀⠀⠀⠀⠀⠀⠀⣀⠹⡪⣣⣟⠵⢫⢞⣞⠞⠢⣪⡪⠀⠀⠀⠀⠀⠀⠂⠁⠁⠀⠁⠅⠀⡀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⡔⢶⣄⠀⠀⠀⠀⡀⢂⠳⣑⡠⠀⡣⡀⡀⡀⣘⢀⠀⡀⡂⢀⠀⢸⢀⠄⡀⢀⠀⡀⠁⠀⠐⠀⠀⢰⡺⡬⡂⠄⠉⢢⣁⢨⢥⣵⡒⠤⣫⡒⠀⠀⠀⠀⠀⠐⠄⠦⠥⢕⢥⡳⠋⠀⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠄⠀⠀⠀⠘⡄⠿⣷⠀⠀⠀⠀⠂⡼⡎⣾⢨⡐⡱⣨⠠⣘⢀⢂⠔⣠⠥⠈⢸⠠⡹⡕⢀⢂⠂⠅⠀⠀⠀⣠⣜⡬⡥⠬⠠⠀⠀⠑⣦⠩⢈⣔⢟⠕⠀⠀⠀⠠⡀⢄⠄⡄⡀⠀⠈⠊⡇⠀⠀⠄⠀⠀⠀⠀⠐⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⣀⠀⠀⠘⢌⠺⢧⡀⠀⠀⡰⣛⣮⡟⠀⠁⠍⢒⡵⢏⡇⠑⠩⠀⠀⠀⢸⠈⠊⢊⠀⢂⠡⠀⠀⠀⢸⠀⢣⢧⣲⢒⠪⡐⡠⡀⠨⠧⢗⠏⠁⠀⠀⡠⢀⠀⢁⠓⡯⣺⠚⠁⢇⡂⠅⠀⠈⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡌⢹⢯⣦⣀⡇⡀⣷⠁⠀⠀⢀⣞⠿⡱⠁⠀⠀⢠⡤⠀⠈⠀⠁⠀⠀⠀⠀⠀⠀⢀⠠⡂⠨⡏⡢⡵⡮⡇⡇⠂⡠⡂⡀⠀⢄⠄⠨⡺⣕⢵⢀⡐⢸⠁⠀⠀⠸⠀⠀⠀⠐⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠣⢄⠈⠘⠸⠠⢨⢗⡄⣀⢠⡟⡎⡂⡁⠀⠀⣴⢿⠐⠀⠀⢀⠀⠀⠀⠀⠀⡀⡂⠁⢔⠄⠀⢃⠇⠀⢹⢑⠥⠻⢽⢜⠀⡼⣕⠅⠘⡝⠁⠀⠀⡂⢑⠀⠀⠀⠈⠀⠀⠀⠀⠠⠀⠡⠀⠄⢀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠄⡀⢅⠀⠈⠳⠂⠅⠉⠀⠮⡻⡣⡞⠗⠁⠀⠀⠀⠀⠀⠀⠀⠀⠔⠨⠀⠁⠀⠠⢄⠐⠁⠀⠈⡊⠄⠀⠈⠕⢘⠀⠀⢁⠈⡂⠀⢀⠀⠐⠁⠀⢌⠨⠂⠄⠀⠀⠈⠀⠡⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⡂⠀⠀⠀⠄⠀⠀⠁⡚⠅⠀⢀⠠⢄⠀⠀⠀⠀⠀⡠⠐⠅⢁⢀⠀⠀⠈⠄⠁⠀⠑⠄⠀⠁⠀⡀⠈⠂⠀⠀⠐⠈⠀⠀⠀⠊⠀⠀⠀⠀⠥⠁⠀⠂⠀⠀⠀⠂⡈⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠒⢠⢀⠁⠀⠀⠀⠀⠀⠀⠨⠀⢂⠝⠄⣀⠀⠀⠀⠀⠀⠀⠀⠐⠀⠀⠀⠀⠀⢄⠀⠸⠁⠔⢕⢔⠄⠀⠠⠐⢀⠀⠀⡀⠌⠄⡀⠀⢀⠀⠀⢀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⣠⡠⡠⡠⢄⢤⠄⠀⠀⠉⠢⢄⠀⠀⠀⠀⠀⠀⠂⠁⠍⡐⢅⠃⠇⢄⠄⡊⠂⠄⠀⠀⠀⠈⢈⠢⠁⠀⠀⠀⠑⠃⠁⠈⠨⡈⠄⠂⠐⡨⠨⠨⢐⠁⠀⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[0m
[38;2;239;68;68m⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⠁⠉⣎⠮⡆⠀⠕⠀⠀⠀⠐⡠⠀⢀⠀⠄⠂⠀⠀⠀⠀⢐⠡⠀⠁⠌⠂⠆⠀⠀⠀⠀⠀⡀⡔⡎⣎⢆⢆⠖⠀⠀⠀⠀⠠⠁⠀⠀⠐⠡⠡⠁⠀⠀⠀⠀⠀⠄⠀⠀⠀⡀⡄⡄⡀⡀⠀[0m


  [38;2;239;68;68m888888 8888888888 .d8888b. 88888888888 8888888888 8888888b.[0m
    [38;2;239;68;68m"88b 888       d88P  Y88b    888     888        888   Y88b[0m
     [38;2;239;68;68m888 888       Y88b.         888     888        888    888[0m
     [38;2;239;68;68m888 8888888    "Y888b.      888     8888888    888   d88P[0m
     [38;2;239;68;68m888 888           "Y88b.    888     888        8888888P"[0m
     [38;2;239;68;68m888 888             "888    888     888        888 T88b[0m
     [38;2;239;68;68m88P 888       Y88b  d88P    888     888        888  T88b[0m
     [38;2;239;68;68m888 8888888888 "Y8888P"     888     8888888888 888   T88b[0m
   [38;2;239;68;68m.d88P[0m
 [38;2;239;68;68m.d88P"[0m
[38;2;239;68;68m888P"[0m



[38;2;239;68;68m.|'''', .|''''|, '||'''|, '\\  //` .|'''',      /.\      |''||''|[0m
[38;2;239;68;68m||      ||    ||  ||   ||   \\//   ||          // \\        ||[0m
[38;2;239;68;68m||      ||    ||  ||...|'    ||    ||         //...\\       ||[0m
[38;2;239;68;68m||      ||    ||  ||         ||    ||        //     \\      ||[0m
[38;2;239;68;68m`|....' `|....|' .||        .||.   `|....' .//       \\.   .||.[0m
  
BANNER_EOF
}

mostrar_aviso() {
cat <<AVISO_EOF
${COR_AVISO}-----------------------------------------------------------------
╔══════════════════════════════════════════════════════════════════════╗
║ [+] Ferramenta de Coleta e Análise de Dados Web                      ║
║ [+] Clona sites inteiros, referenciais, API, robots e imagens.       ║
║ [+] Use como quiser - o que fizer fica por sua conta│Versão: 1.0.0   ║
╚══════════════════════════════════════════════════════════════════════╝

[*] Sistema de Operações — o que faz)

    [1] Coletar Dados de uma URL
    [2] Analisar Página Completa
    [3] Buscar APIs e Endpoints
-----------------------------------------------------------------${COR_RESET}
AVISO_EOF
}

erro() { echo "[Jester] ERRO: $*" >&2; exit 1; }

# --------------------------------------------------------- checagens essenciais
command -v python3 >/dev/null 2>&1 || erro "python3 não encontrado. No Termux: pkg install python"
[ -f "$CORE" ] || erro "não achei core/jestercopy.py ao lado deste script ($SCRIPT_DIR)."

python3 - <<'PYCHECK' 2>/dev/null
import sys
try:
    import requests, bs4, lxml  # noqa
except ImportError as e:
    sys.exit(1)
PYCHECK
if [ $? -ne 0 ]; then
    echo "[Jester] Dependências Python faltando (requests/beautifulsoup4/lxml)."
    echo "          Rode primeiro:  bash install.sh"
    exit 1
fi

clear 2>/dev/null || true
echo "${COR_TITULO}"
mostrar_banner
echo "${COR_RESET}"
mostrar_aviso
echo

# --------------------------------------------------------- modo de uso
# Uso direto (não-interativo), repassando tudo pro núcleo:
#   ./jester.sh exemplo.com [--out pasta] [--workers N] [--max-pages N] ...
# Uso interativo (sem argumentos): pergunta o essencial na tela.
ARGS=("$@")

if [ "${#ARGS[@]}" -eq 0 ]; then
    read -r -p "[38;2;239;68;68m uØa§_jester:~ [32m§> " ALVO
    [ -n "$ALVO" ] || erro "nenhum alvo informado."

    read -r -p "Pasta de saída [jester_output]: " SAIDA
    SAIDA="${SAIDA:-jester_output}"

    read -r -p "Conexões simultâneas [8]: " WORKERS
    WORKERS="${WORKERS:-8}"

    read -r -p "Ignorar robots.txt? (só em domínio próprio) [s/N]: " IGNRB
    ARGS=("$ALVO" "--out" "$SAIDA" "--workers" "$WORKERS")
    case "$IGNRB" in
        s|S|sim|SIM) ARGS+=("--ignore-robots") ;;
    esac
    echo
fi

echo "${COR_TITULO}[Jester] Iniciando clonagem...${COR_RESET}"
echo

python3 "$CORE" "${ARGS[@]}"
STATUS=$?

if [ $STATUS -ne 0 ]; then
    echo
    echo "[Jester] A clonagem terminou com erro (código $STATUS). Veja as mensagens acima."
    exit $STATUS
fi

# --------------------------------------------------------- extras opcionais (C++ / PHP)
# Descobre a última pasta de saída usada (melhor esforço: procura o
# diretório passado em --out, ou o padrão).
SAIDA_USADA="jester_output"
for ((i = 0; i < ${#ARGS[@]}; i++)); do
    if [ "${ARGS[$i]}" = "--out" ] && [ $((i + 1)) -lt ${#ARGS[@]} ]; then
        SAIDA_USADA="${ARGS[$((i + 1))]}"
    fi
done

if [ -x "$TOOLS/checksum" ] && [ -d "$SAIDA_USADA" ]; then
    echo
    read -r -p "Rodar verificação de integridade/duplicados em C++ agora? [S/n]: " RODAR_CKSUM
    case "$RODAR_CKSUM" in
        n|N|nao|não|NAO|NÃO) ;;
        *) echo "${COR_OK}[Jester] Rodando checksum...${COR_RESET}"; "$TOOLS/checksum" "$SAIDA_USADA" ;;
    esac
fi

if command -v php >/dev/null 2>&1 && [ -f "$TOOLS/router.php" ] && [ -d "$SAIDA_USADA" ]; then
    echo
    read -r -p "Subir um preview local do clone com PHP agora? [s/N]: " RODAR_PHP
    case "$RODAR_PHP" in
        s|S|sim|SIM)
            PORTA=8080
            PRIMEIRA_PASTA="$(find "$SAIDA_USADA" -maxdepth 1 -mindepth 1 -type d | head -n1)"
            ALVO_PREVIEW="${PRIMEIRA_PASTA:-$SAIDA_USADA}"
            echo "${COR_OK}[Jester] Preview em http://127.0.0.1:$PORTA/  (Ctrl+C para parar)${COR_RESET}"
            (cd "$ALVO_PREVIEW" && php -S "127.0.0.1:$PORTA" "$TOOLS/router.php")
            ;;
    esac
fi

echo
echo "${COR_OK}[Jester] Concluído.${COR_RESET}"
