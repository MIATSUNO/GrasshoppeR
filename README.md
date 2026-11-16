# GrasshoppeR Suite

**Uma central de ferramentas de terminal, com programas independentes em diferentes linguagens.**

A **GrasshoppeR Suite** reúne utilitários de diagnóstico de rede, inspeção de arquivos, reconhecimento de tecnologias web, pesquisa de presença pública de usernames, coleta de páginas e recursos web e integração com ferramentas externas de auditoria.

O projeto foi pensado especialmente para **Termux no Android**, mantendo compatibilidade com ambientes Linux que ofereçam os runtimes necessários.

A proposta central é simples: cada programa conserva sua própria identidade, linguagem e especialidade; a GrasshoppeR oferece um ponto de entrada para organizar e executar boa parte desse conjunto.

> **Inspirações:** algumas ferramentas e ideias do projeto foram inspiradas em programas que já existem no ecossistema de segurança e análise, incluindo **AliensEye** e **WhatWeb**. Essas referências são inspirações conceituais; os programas desta suíte possuem implementação, organização, interface e conjunto de recursos próprios.

---

## Índice

- [Visão geral](#visão-geral)
- [Novidades e destaques](#novidades-e-destaques)
- [Requisitos](#requisitos)
- [Instalação no Termux](#instalação-no-termux)
- [Instalação no Debian e Ubuntu](#instalação-no-debian-e-ubuntu)
- [Dependências Python](#dependências-python)
- [Dependências por programa](#dependências-por-programa)
- [Como iniciar a GrasshoppeR](#como-iniciar-a-grasshopper)
- [1. GrasshoppeR Launcher](#1-grasshopper-launcher)
- [2. Network Tools](#2-network-tools)
- [3. File Tools](#3-file-tools)
- [4. MoonScan](#4-moonscan)
- [5. Rasco OSINT](#5-rasco-osint)
- [6. Mianba](#6-mianba)
- [7. JesterCopyCat / Jester](#7-jestercopycat--jester)
- [8. Componentes auxiliares da Jester](#8-componentes-auxiliares-da-jester)
- [9. Pentest Tools](#9-pentest-tools)
- [Executar programas individualmente](#executar-programas-individualmente)
- [Adicionar ferramentas à GrasshoppeR](#adicionar-ferramentas-à-grasshopper)
- [Testes automatizados](#testes-automatizados)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Tecnologias](#tecnologias)
- [Créditos e inspirações](#créditos-e-inspirações)

---

## Visão geral

A GrasshoppeR é composta por módulos próprios e programas independentes:

| Programa | Linguagem | Objetivo |
|---|---|---|
| **GrasshoppeR** | Python | Launcher e central de execução |
| **Network Tools** | Python | Consultas DNS, HTTP, TLS e conectividade TCP |
| **File Tools** | Python | Hashes, metadados, manifestos e inspeção ZIP |
| **MoonScan** | Go | Fingerprinting e análise técnica de aplicações web |
| **Rasco OSINT** | Python | Pesquisa de usernames em serviços públicos |
| **Mianba** | Python | Painel de diagnóstico e informações de rede |
| **JesterCopyCat / Jester** | Shell + Python | Coleta e organização de páginas e recursos web |
| **FastFetch** | Go | Componente auxiliar de sitemap e download em lote da Jester |
| **Extract Links** | JavaScript | Extração complementar de referências em JavaScript |
| **Router** | PHP | Pré-visualização local dos arquivos coletados |
| **Checksum** | C++17 | Manifesto de integridade e identificação de duplicados |
| **Pentest Tools** | Python | Adaptadores para ferramentas externas instaladas no sistema |

A disponibilidade de cada componente depende do runtime correspondente. Os componentes auxiliares da Jester são opcionais: quando um deles não está instalado, o núcleo Python mantém os recursos essenciais que consegue executar por conta própria.

## Novidades e destaques

- Launcher central com descoberta automática de programas em `tools/`.
- Suporte a diferentes linguagens e extensões.
- Menus próprios para rede e arquivos.
- Execução individual dos programas, sem obrigar o uso do launcher.
- MoonScan em Go, com catálogo de assinaturas tecnológicas, modos padrão e profundo e relatórios JSON.
- Rasco com catálogo categorizado, estados de resultado, relatórios e histórico SQLite.
- Mianba com painel visual de consultas de rede.
- Jester com crawler de páginas, coleta de recursos, detecção de referências a APIs e relatórios.
- Componentes auxiliares em Go, JavaScript, PHP e C++ para ampliar o fluxo da Jester.
- Pentest Tools separado do menu principal, mas executável diretamente pelo terminal.
- Instalação organizada por runtimes e bibliotecas, com componentes opcionais.

---

# Requisitos

## Ambiente recomendado

- Android com Termux atualizado; ou
- Debian / Ubuntu;
- Python 3.10 ou superior;
- acesso ao gerenciador de pacotes da distribuição;
- espaço livre para instalar runtimes, bibliotecas e armazenar resultados.

## Runtimes por linguagem

| Runtime / ferramenta | Utilizado por |
|---|---|
| Python 3 | Launcher, Network Tools, File Tools, Rasco, Mianba, Jester e Pentest Tools |
| Bash | `jester.sh` e instaladores |
| Go | MoonScan e FastFetch |
| Node.js | Extrator complementar da Jester |
| PHP CLI | Pré-visualizador local da Jester |
| Compilador C++17 | Checksum |

---

# Instalação no Termux

Os comandos abaixo instalam os runtimes e utilitários necessários para os componentes da suíte.

## 1. Atualizar o Termux

```bash
pkg update -y && pkg upgrade -y
```

## 2. Instalar runtimes, compiladores e utilitários

```bash
pkg install -y \
  python \
  clang \
  golang \
  php \
  nodejs \
  traceroute \
  dnsutils \
  whois \
  iproute2 \
  coreutils \
  findutils \
  git \
  curl
```

### Para que serve cada pacote?

| Pacote Termux | Utilização |
|---|---|
| `python` | Launcher e módulos Python |
| `clang` | Compilação C/C++ e Checksum |
| `golang` | Compilação do MoonScan e FastFetch |
| `php` | Pré-visualização local da Jester |
| `nodejs` | Extração complementar de referências JavaScript |
| `traceroute` | Rota de rede utilizada pelo Mianba |
| `dnsutils` | Utilitários DNS do ambiente |
| `whois` | Consulta WHOIS do Mianba |
| `iproute2` | Interfaces e rotas de rede |
| `coreutils` | Comandos básicos do sistema |
| `findutils` | Localização de arquivos e diretórios |
| `git` | Clonagem do repositório |
| `curl` | Consultas HTTP pelo terminal e operações auxiliares |

## 3. Obter o projeto

Se estiver instalando pelo GitHub:

```bash
git clone URL_DO_REPOSITORIO
cd Grasshopper-Suite
```

Substitua `URL_DO_REPOSITORIO` pelo endereço real do repositório.

Se você já possui o ZIP, extraia-o e entre na pasta que contém `Grasshopper.py`.

## 4. Instalar as bibliotecas Python

A suíte utiliza estas bibliotecas externas:

```bash
python -m pip install requests beautifulsoup4 lxml rich colorama
```

Ou, utilizando o arquivo de requisitos:

```bash
python -m pip install -r requests.txt
```

**Observação sobre o arquivo `requests.txt`:** na versão deste pacote, ele lista `beautifulsoup4`, `colorama`, `requests` e `rich`. O núcleo da Jester também importa `lxml`; por isso, instale `lxml` separadamente caso ele ainda não esteja disponível:

```bash
python -m pip install lxml
```

## 5. Compilar o MoonScan

A partir da raiz do projeto:

```bash
cd tools
go build -o moonscan moonscan.go
chmod +x moonscan
cd ..
```

Executar:

```bash
./tools/moonscan --help
```

## 6. Compilar o FastFetch da Jester

A partir da raiz do projeto:

```bash
cd tools/tools
go build -o fastfetch fastfetch.go
chmod +x fastfetch
cd ../..
```

O núcleo da Jester procura o binário `fastfetch` nesse diretório. Sem ele, a Jester continua utilizando o fluxo Python.

## 7. Compilar o Checksum

A partir da raiz do projeto:

```bash
cd tools/tools
clang++ -std=c++17 -O2 -Wall -Wextra -o checksum checksum.cpp
chmod +x checksum
cd ../..
```

O Checksum é opcional. Sem o executável compilado, a coleta principal da Jester continua disponível; o relatório adicional de integridade não será gerado.

## 8. Permissões dos scripts

```bash
chmod +x tools/jester.sh
chmod +x install.sh
```

## 9. Iniciar

```bash
python Grasshopper.py
```

---

# Instalação no Debian e Ubuntu

Atualize os índices:

```bash
sudo apt update
```

Instale os runtimes e utilitários:

```bash
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-requests \
  python3-bs4 \
  python3-lxml \
  python3-rich \
  python3-colorama \
  golang-go \
  build-essential \
  php-cli \
  nodejs \
  npm \
  traceroute \
  dnsutils \
  whois \
  iproute2 \
  coreutils \
  findutils \
  git \
  curl
```

Se a distribuição não disponibilizar alguma biblioteca Python como pacote `python3-*`, utilize um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install requests beautifulsoup4 lxml rich colorama
```

Compile MoonScan, FastFetch e Checksum seguindo os passos da seção do Termux, a partir da raiz do projeto.

---

# Dependências Python

As bibliotecas de terceiros utilizadas pelos módulos Python são:

| Pacote pip | Import utilizado | Programas |
|---|---|---|
| `requests` | `requests` | Mianba, Rasco e Jester |
| `beautifulsoup4` | `bs4` | Jester |
| `lxml` | `lxml` | Parser HTML/XML da Jester |
| `rich` | `rich` | Rasco e Mianba |
| `colorama` | `colorama` | Launcher GrasshoppeR |

Instalação completa:

```bash
python -m pip install requests beautifulsoup4 lxml rich colorama
```

## Bibliotecas que não precisam de pip

Os módulos abaixo são da biblioteca padrão do Python:

- `argparse`
- `concurrent.futures`
- `contextlib`
- `csv`
- `dataclasses`
- `datetime`
- `hashlib`
- `html`
- `ipaddress`
- `json`
- `math`
- `os`
- `pathlib`
- `random`
- `re`
- `select`
- `shlex`
- `shutil`
- `signal`
- `socket`
- `sqlite3`
- `ssl`
- `stat`
- `subprocess`
- `sys`
- `tempfile`
- `threading`
- `time`
- `tty`
- `unicodedata`
- `urllib`
- `uuid`
- `zipfile`

Não é necessário instalar esses módulos separadamente.

---

# Dependências por programa

## GrasshoppeR Launcher

**Arquivo:** `Grasshopper.py`

Necessita:

```bash
python -m pip install colorama
```

Também importa os módulos locais `network_tools.py` e `file_tools.py`, que acompanham o projeto.

## Network Tools

**Arquivo:** `network_tools.py`

Utiliza apenas bibliotecas da biblioteca padrão do Python.

Não exige instalação adicional via pip.

## File Tools

**Arquivo:** `file_tools.py`

Utiliza apenas bibliotecas da biblioteca padrão do Python.

Não exige instalação adicional via pip.

## MoonScan

**Arquivo:** `tools/moonscan.go`

Não utiliza bibliotecas externas Go no código fornecido. É compilado com o Go instalado no sistema:

```bash
cd tools
go build -o moonscan moonscan.go
```

## Rasco OSINT

**Arquivo:** `tools/RascoOsint.py`

Necessita:

```bash
python -m pip install requests rich
```

O histórico utiliza SQLite, incluído na biblioteca padrão do Python.

## Mianba

**Arquivo:** `tools/mianba.py`

Necessita:

```bash
python -m pip install requests rich
```

Também utiliza o comando externo `traceroute` para a função de rota e `whois` para consultas WHOIS.

No Termux:

```bash
pkg install traceroute whois iproute2 dnsutils
```

## Jester

**Arquivo de entrada:** `tools/jester.sh`  
**Núcleo:** `tools/core/jestercopy.py`

Dependências Python:

```bash
python -m pip install requests beautifulsoup4 lxml
```

Componentes opcionais:

| Componente | Dependência | Função |
|---|---|---|
| FastFetch | Go | Sitemap e transferências em lote |
| Extract Links | Node.js | Extração complementar em JavaScript |
| Router | PHP CLI | Pré-visualização local |
| Checksum | Compilador C++17 | Manifesto e duplicados |

## Pentest Tools

**Arquivo:** `pentest_tools.py`

O módulo utiliza somente a biblioteca padrão do Python para seu código de integração.

As ferramentas externas chamadas pelo módulo são programas independentes. O Python não as instala automaticamente. O catálogo de executáveis reconhecidos está descrito na seção [Pentest Tools](#9-pentest-tools).

---

# Como iniciar a GrasshoppeR

Na raiz do projeto:

```bash
python Grasshopper.py
```

O launcher apresenta o banner e o menu principal.

## Menu principal desta versão

```text
[1] Rede
[2] Arquivos
[3] Cricket-Term
[4] MoonScan
[5] Rasco
[6] Mianba
[7] JesterCopyCat

[?] Ajuda                 [0] Sair
```

| Opção | Programa | O que abre |
|---|---|---|
| `1` | Rede | Menu Network Tools |
| `2` | Arquivos | Menu File Tools |
| `3` | Cricket-Term | Terminal de comandos do sistema |
| `4` | MoonScan | Programa MoonScan localizado em `tools/` |
| `5` | Rasco | Rasco OSINT |
| `6` | Mianba | Painel Mianba |
| `7` | JesterCopyCat | Interface Shell da Jester |
| `?` | Ajuda | Informações do launcher |
| `0` | Sair | Encerra a sessão |

**Pentest Tools é executado separadamente pelo terminal** nesta versão. Ele não aparece no menu principal.

## Descoberta de programas

O launcher procura programas na pasta `tools/` e em subpastas, ignorando diretórios de cache e ambientes virtuais conhecidos.

Entre as extensões reconhecidas estão:

| Linguagem / formato | Extensões |
|---|---|
| Python | `.py`, `.pyw` |
| Shell | `.sh`, `.bash`, `.command`, `.zsh`, `.fish` |
| JavaScript | `.js`, `.mjs`, `.cjs` |
| Ruby | `.rb` |
| Perl | `.pl` |
| PHP | `.php` |
| Lua | `.lua` |
| R | `.r` |
| Swift | `.swift` |
| Go | `.go` |
| PowerShell | `.ps1` |
| Windows Script | `.bat`, `.cmd`, `.vbs` |
| Java | `.jar` |
| Executáveis nativos | `.exe`, `.com`, `.bin`, `.out` e arquivos executáveis sem extensão |

O runtime correspondente precisa estar instalado e acessível pelo `PATH`.

---

# 1. GrasshoppeR Launcher

![Foto da GrasshoppeR](imagens/grass.png)

**Arquivo:** `Grasshopper.py`  
**Linguagem:** Python

A GrasshoppeR é o ponto central de acesso à suíte.

### Recursos

- Banner e interface colorida de terminal.
- Menu principal.
- Menus próprios para rede e arquivos.
- Descoberta de ferramentas em subpastas.
- Suporte a múltiplas linguagens.
- Verificação de disponibilidade de runtimes.
- Verificação de sintaxe para programas Python antes da execução.
- Confirmação antes de iniciar programas externos.
- Execução acompanhada no terminal.
- Histórico de execuções durante a sessão.
- Possibilidade de encerrar processos externos iniciados pelo launcher.
- Modo Cricket-Term.

### Cricket-Term

O Cricket-Term permite executar comandos do ambiente sem sair da GrasshoppeR.

Ele é um terminal integrado ao launcher, não um interpretador de comandos exclusivo da suíte.

---

# 2. Network Tools

**Arquivo:** `network_tools.py`  
**Linguagem:** Python

O Network Tools reúne consultas e verificações de conectividade em um menu próprio.

## Menu

```text
[1] Consulta DNS
[2] Cabeçalhos HTTP
[3] Certificado TLS
[4] Verificar portas TCP
[0] Voltar
```

### 2.1 Consulta DNS

Resolve um hostname e apresenta os endereços retornados pelo sistema.

### 2.2 Cabeçalhos HTTP

Consulta uma URL e apresenta o código HTTP e os cabeçalhos recebidos.

### 2.3 Certificado TLS

Abre uma conexão TLS e apresenta informações do certificado apresentado pelo servidor.

### 2.4 Verificar portas TCP

Permite verificar portas TCP informadas individualmente, com validação da entrada e timeout configurável.

O módulo também pode ser consultado individualmente:

```bash
python network_tools.py --help
```

### Diferencial

É um conjunto leve de verificações implementadas diretamente em Python, sem exigir que cada consulta dependa de um programa externo.

---

# 3. File Tools

**Arquivo:** `file_tools.py`  
**Linguagem:** Python

O File Tools reúne funções para inspeção e comparação de arquivos.

## Menu

```text
[1] SHA-256 de arquivo
[2] Metadados de arquivo
[3] Criar manifest
[4] Comparar manifest
[5] Inspecionar Zipes (.zip)
[0] Voltar
```

### 3.1 SHA-256

Calcula o hash SHA-256 de um arquivo.

### 3.2 Metadados

Apresenta informações como tamanho e datas do arquivo.

### 3.3 Criar manifesto

Percorre um diretório e registra informações e hashes dos arquivos encontrados.

### 3.4 Comparar manifestos

Compara dois manifestos e organiza diferenças em arquivos adicionados, removidos ou modificados.

### 3.5 Inspecionar ZIP

Lista membros e metadados de arquivos compactados ZIP.

### Diferencial

O módulo oferece uma forma prática de registrar e comparar o estado de diretórios, além de verificar arquivos individuais.

---

# 4. MoonScan
![Print da MoonScan](imagens/mscan.png)


**Arquivo:** `tools/moonscan.go`  
**Linguagem:** Go  
**Versão indicada no código:** `1.0.0`

O MoonScan é um analisador de aplicações web voltado ao reconhecimento de tecnologias, características HTTP e informações técnicas de um alvo.

É uma das ferramentas independentes da suíte e pode ser executada pelo launcher ou diretamente pelo terminal.

## Recursos

### Fingerprinting tecnológico

O MoonScan utiliza assinaturas para procurar evidências de tecnologias em:

- Cabeçalhos HTTP.
- Cookies.
- HTML.
- Metadados.
- Scripts e referências.
- Caminhos e recursos identificáveis.
- Características de respostas do servidor.

### Categorias

O catálogo de assinaturas abrange diferentes tipos de tecnologias, incluindo:

- Servidores web.
- Linguagens e ambientes.
- Frameworks.
- CMS.
- Bibliotecas JavaScript.
- Plataformas de comércio eletrônico.
- CDNs.
- Serviços de terceiros.
- Ferramentas de análise.
- Tecnologias de proteção e infraestrutura.

### Informações técnicas

Os resultados podem incluir:

- IP resolvido.
- Dados aproximados de geolocalização do IP.
- Informações TLS.
- Certificado apresentado.
- Cabeçalhos HTTP.
- Cookies e evidências adicionais no modo detalhado.
- Tecnologias identificadas.
- Nível de confiança das assinaturas.
- Evidências que justificam cada identificação.

### Modos

- **Padrão:** análise leve com requisição inicial, cabeçalhos e assinaturas.
- **Deep:** análise adicional com baseline e sondagens de caminhos.

### Relatórios

O MoonScan apresenta resultados no terminal e pode gerar relatórios JSON.

## Executar

A partir da raiz:

```bash
./tools/moonscan --help
```

Se o binário ainda não foi compilado:

```bash
cd tools
go build -o moonscan moonscan.go
cd ..
```

## Opções documentadas

| Opção | Função |
|---|---|
| `-h`, `--help` | Ajuda |
| `-V`, `--version` | Versão |
| `-v`, `--verbose` | Evidências e informações adicionais |
| `-a`, `--deep` | Modo profundo |
| `-l`, `--list ARQ` | Arquivo com alvos, um por linha |
| `-t`, `--threads N` | Número de alvos em paralelo |
| `-T`, `--timeout S` | Timeout |
| `-A`, `--agent UA` | User-Agent |
| `-H`, `--header` | Cabeçalho adicional; pode ser repetido |
| `-c`, `--cookie` | Cookie |
| `-x`, `--proxy` | Proxy HTTP, HTTPS ou SOCKS5 |
| `-k`, `--insecure` | Não validar certificado TLS |
| `--no-follow` | Não seguir redirecionamentos |
| `--no-geo` | Desativar consulta de geolocalização |
| `-o`, `--output ARQ` | Caminho do relatório JSON |
| `--json` | Imprimir somente JSON |
| `--no-report` | Não salvar relatório |
| `--no-color` | Desativar cores |
| `--color` | Forçar cores |
| `--no-banner` | Ocultar banner |
| `--techs` | Listar categorias e tecnologias |
| `-i`, `--console` | Abrir console interativo |

## Console interativo

Inicie sem argumentos:

```bash
./tools/moonscan
```

Comandos do console:

| Comando | Função |
|---|---|
| `scan` | Análise padrão |
| `deep` | Análise profunda |
| `batch` | Processamento de arquivo de alvos |
| `set` | Alterar configuração |
| `show` | Exibir configuração |
| `techs` | Listar tecnologias |
| `banner` | Exibir banner |
| `clear` | Limpar tela |
| `help` | Ajuda |
| `exit` | Sair |

As consultas devem ser realizadas somente em sistemas próprios ou com autorização do responsável.

---

# 5. Rasco OSINT
![Print da Rasco](imagens/rasco.png)


**Arquivo:** `tools/RascoOsint.py`  
**Linguagem:** Python  
**Interface:** Rich  
**Banco de dados:** SQLite

O Rasco é uma ferramenta de pesquisa de presença pública de usernames em serviços online.

Seu catálogo reúne sites de diferentes categorias e organiza as respostas em resultados que podem ser exportados, armazenados e comparados.

## Categorias do catálogo

- Desenvolvimento.
- Redes sociais.
- Música.
- Jogos.
- Vídeo.
- Arte e design.
- Escrita e blogs.
- Criadores e links.
- Comunidades.
- Idiomas.
- Referência.
- Segurança.

## Modos de pesquisa

- **Rápido:** utiliza fontes selecionadas para uma consulta mais curta.
- **Completo:** percorre o catálogo selecionado.
- **Demo:** apresenta o fluxo demonstrativo.

O programa também oferece seleção por categoria e geração de variações de username.

## Estados dos resultados

| Estado | Significado |
|---|---|
| `FOUND` | Evidência de perfil encontrado |
| `MAYBE` | Resultado inconclusivo ou parcial |
| `NOT_FOUND` | Perfil não identificado |
| `MANUAL` | Conferência manual necessária |
| `SKIPPED` | Fonte não consultada |
| `CAPTCHA` | Desafio apresentado pela fonte |
| `RATE_LIMITED` | Limite de consultas atingido |
| `RESTRICTED` | Acesso restrito |
| `TIMEOUT` | Tempo limite |
| `ERROR` | Erro durante a consulta |

## Relatórios

O Rasco pode exportar:

- JSON.
- CSV.
- HTML.

## Histórico SQLite

O programa registra pesquisas anteriores no banco local e permite consultar e comparar resultados.

Os registros incluem informações como username, modo, data, duração e quantidade de resultados.

## Executar

```bash
python tools/RascoOsint.py --help
```

O modo interativo também pode ser iniciado diretamente:

```bash
python tools/RascoOsint.py
```

### Diferencial

O Rasco combina um catálogo categorizado, classificação dos resultados, exportação em vários formatos e histórico persistente. A proposta é organizar a pesquisa em registros consultáveis, em vez de apresentar somente uma sequência de links.

---

# 6. Mianba
![Imagem da Mianba(mi@nb@)](imagens/mianba.png)


**Arquivo:** `tools/mianba.py`  
**Linguagem:** Python  
**Interface:** Rich

O Mianba é um painel de informações e diagnóstico de rede, desenvolvido com foco na utilização em terminais móveis.

## Menu

| Código | Módulo | Descrição |
|---|---|---|
| `01` | Meu IP | IP público, IP local, hostname e dados aproximados do provedor |
| `02` | Consultar IP / domínio | Resolução, DNS reverso e dados aproximados |
| `03` | Traceroute | Caminho de rede e saltos |
| `04` | Scanner TCP | Consulta de portas TCP |
| `05` | Consulta DNS | Registros A, AAAA, MX, NS, TXT, CNAME e SOA |
| `06` | WHOIS | Dados públicos de registro |
| `07` | Interfaces | Interfaces e rotas locais |
| `00` | Sair | Encerrar |

### Meu IP

Apresenta IP público, IP local e hostname. Quando disponível, complementa o resultado com informações aproximadas de país, região, cidade, provedor, organização e ASN.

### Consultar IP / domínio

Resolve o host, consulta o DNS reverso e apresenta informações adicionais disponíveis.

### Traceroute

Apresenta os saltos identificados no caminho até o host informado.

### Scanner TCP

Organiza o resultado de consultas de portas em uma tabela com possíveis nomes de serviços associados às portas conhecidas.

### Consulta DNS

Apresenta os tipos de registros DNS implementados no módulo.

### WHOIS

Exibe dados públicos retornados pelo utilitário WHOIS instalado no ambiente.

### Interfaces

Apresenta endereços e informações de interfaces e rotas locais.

## Executar

```bash
python tools/mianba.py
```

### Diferencial

O Mianba reúne várias consultas em uma interface visual única, utilizando tabelas, painéis e cores adaptáveis ao terminal.

---

# 7. JesterCopyCat / Jester
![Foto Banner Jester](imagens/jester.png)

**Interface:** `tools/jester.sh`  
**Núcleo:** `tools/core/jestercopy.py`  
**Linguagens:** Shell e Python

A Jester é a ferramenta de coleta e organização de páginas e recursos web da suíte.

O script Shell apresenta a interface e encaminha as opções para o núcleo Python.

## Modos apresentados

```text
[1] Coletar Dados de uma URL
[2] Analisar Página Completa
[3] Buscar APIs e Endpoints
```

Sem argumentos, o script solicita o endereço e as opções básicas interativamente.

## Coleta de páginas

O núcleo percorre páginas HTML do domínio-alvo utilizando uma fila de páginas e workers concorrentes.

## Coleta de recursos

A Jester identifica e baixa referências de recursos, incluindo:

- HTML.
- CSS.
- JavaScript.
- JSON.
- XML.
- TXT.
- Imagens.
- Vídeos.
- Áudios.
- Fontes.
- Documentos.
- Arquivos compactados.

A classificação de recursos permite organizar páginas navegáveis separadamente de arquivos estáticos.

## Extração de referências HTML

A análise considera:

- Links `href`.
- Imagens `src`.
- Scripts.
- Folhas de estilo.
- Elementos de áudio e vídeo.
- Iframes.
- Embeds.
- Objetos.
- `srcset`.
- Metadados Open Graph.
- Metadados do Twitter.
- CSS inline.
- Blocos `<style>`.

## Extração CSS

A Jester identifica URLs em declarações `url(...)` e referências `@import`.

## Extração JavaScript

O núcleo Python identifica caminhos de recursos por padrões de texto e pode chamar o extrator Node.js para complementar a análise.

## Detecção de APIs e endpoints

O detector próprio procura referências em padrões como:

- `fetch()`.
- `axios`.
- `$.get()`, `$.post()` e `$.ajax()`.
- `XMLHttpRequest.open()`.
- Caminhos `/api/`.
- Referências GraphQL.
- Caminhos `/rest/`.
- Segmentos versionados como `/v1/`, `/v2/` e `/v3/`.
- Referências `wp-json`.

Os resultados são consolidados em um relatório `api+<domínio>.txt`.

## Sitemap

Quando o FastFetch está compilado e disponível, a Jester pode consultar `robots.txt`, sitemaps e índices de sitemaps para localizar páginas adicionais.

Sem o acelerador Go, o crawler Python continua funcionando.

## Arquivos de saída

A Jester cria um diretório de saída para armazenar as páginas e os recursos.

Relatórios adicionais incluem:

| Arquivo | Conteúdo |
|---|---|
| `api+<domínio>.txt` | Endpoints identificados |
| `falhas.txt` | Falhas registradas durante a coleta |
| `paginas_externas_ignoradas.txt` | Páginas externas que não foram seguidas como páginas do alvo |

A saída também apresenta estatísticas de páginas, arquivos, bytes transferidos e falhas.

## Executar interativamente

```bash
bash tools/jester.sh
```

O programa perguntará:

1. URL ou domínio inicial.
2. Diretório de saída.
3. Quantidade de conexões simultâneas.
4. Se deve ignorar `robots.txt`.

## Executar com argumentos

```bash
bash tools/jester.sh https://seu-dominio.example
```

O núcleo Python também pode ser executado diretamente:

```bash
python tools/core/jestercopy.py --help
```

Opções disponíveis no núcleo incluem:

- `--out`: diretório de saída.
- `--workers`: quantidade de workers.
- `--max-pages`: limite de páginas.
- `--max-files`: limite de arquivos.
- `--delay`: intervalo entre requisições.
- `--timeout`: timeout.
- `--ignore-robots`: não utilizar a regra de `robots.txt`.
- `--min-free-mb`: espaço livre mínimo.

Utilize a Jester somente em sites próprios ou em projetos cuja coleta tenha sido autorizada.

### Diferencial

A Jester combina coleta de páginas, download de recursos, extração de referências em HTML/CSS/JavaScript e identificação textual de endpoints. Os relatórios separam os resultados por tipo, facilitando a consulta posterior.

---

# 8. Componentes auxiliares da Jester

## FastFetch

**Arquivo:** `tools/tools/fastfetch.go`  
**Linguagem:** Go

O FastFetch é um acelerador opcional da Jester.

Possui dois modos internos:

- `sitemap`: consulta `robots.txt`, sitemaps e índices de sitemaps para devolver URLs de páginas.
- `fetch`: recebe URLs e caminhos de destino pelo `stdin` e realiza transferências em lote com workers Go.

O núcleo Python procura o executável compilado em `tools/tools/fastfetch`.

Compilação:

```bash
cd tools/tools
go build -o fastfetch fastfetch.go
chmod +x fastfetch
cd ../..
```

## Extract Links

**Arquivo:** `tools/tools/extract_links.js`  
**Linguagem:** JavaScript / Node.js

Complementa a extração de referências em arquivos JavaScript.

Reconhece padrões como:

- `import`.
- `export ... from`.
- `require()`.
- `import()`.
- `new URL()`.
- `sourceMappingURL`.
- Strings com extensões de recursos reconhecidas.

O resultado é emitido como JSON para o núcleo Python.

Não exige pacotes npm externos.

## Router

**Arquivo:** `tools/tools/router.php`  
**Linguagem:** PHP

O Router é um pré-visualizador local dos arquivos coletados pela Jester.

Ele resolve rotas limpas procurando arquivos `.html` correspondentes e também procura `index.html` em diretórios.

O script Shell pode oferecer a inicialização do preview após a coleta, caso PHP esteja disponível.

O servidor de pré-visualização é iniciado localmente pelo PHP CLI.

## Checksum

**Arquivo:** `tools/tools/checksum.cpp`  
**Linguagem:** C++17

O Checksum percorre o diretório de saída e calcula um hash FNV-1a de 64 bits para cada arquivo.

Gera:

- `manifesto.tsv`: hash, tamanho em bytes e caminho relativo.
- `duplicados.txt`: grupos de arquivos com o mesmo hash.

Compilação:

```bash
cd tools/tools
clang++ -std=c++17 -O2 -Wall -Wextra -o checksum checksum.cpp
chmod +x checksum
cd ../..
```

O Jester Shell procura o executável em `tools/tools/checksum` e pode oferecer a execução após a coleta.

---

# 9. Pentest Tools

**Arquivo:** `pentest_tools.py`  
**Linguagem:** Python  
**Integração:** executáveis externos do sistema

O Pentest Tools é um módulo independente de integração com utilitários externos. Ele não aparece no menu principal da GrasshoppeR, mas pode ser executado diretamente a partir da raiz do projeto.

O arquivo não instala os programas externos: ele localiza os executáveis no `PATH` e chama o programa correspondente.

## Como abrir a ajuda

```bash
python pentest_tools.py --help
```

O comando apresenta as ferramentas reconhecidas pelo catálogo.

## Ferramentas reconhecidas

| Nome no catálogo | Executável procurado | Descrição |
|---|---|---|
| `nmap` | `nmap` | Descoberta e inventário de rede |
| `tcpdump` | `tcpdump` | Captura de pacotes |
| `tshark` | `tshark` | Análise de pacotes pela linha de comando |
| `netcat` | `nc` | Conexão TCP |
| `nikto` | `nikto` | Análise de servidor web |
| `sqlmap` | `sqlmap` | Auditoria de aplicações SQL |
| `gobuster` | `gobuster` | Descoberta de caminhos web |
| `wpscan` | `wpscan` | Análise de instalações WordPress |
| `sslscan` | `sslscan` | Inspeção de protocolos e cifras TLS |
| `hydra` | `hydra` | Integração de auditoria de credenciais |
| `medusa` | `medusa` | Integração de auditoria de credenciais |
| `john` | `john` | Análise de hashes com John the Ripper |
| `hashcat` | `hashcat` | Análise de hashes com Hashcat |
| `aircrack-ng` | `aircrack-ng` | Análise de arquivos de captura Wi-Fi |
| `ettercap` | `ettercap` | Consulta de versão do Ettercap |
| `searchsploit` | `searchsploit` | Pesquisa em base local Exploit-DB |
| `binwalk` | `binwalk` | Inspeção de assinaturas e estruturas de arquivos |
| `radare2` | `r2` | Análise estática de binários |

## Como o módulo funciona

1. Recebe o nome da ferramenta e os argumentos.
2. Consulta o catálogo `TOOL_CATALOG`.
3. Localiza o executável com `shutil.which()`.
4. Monta a lista de argumentos.
5. Executa o binário como processo externo.
6. Captura `stdout`, `stderr` e código de retorno.
7. Imprime um resultado serializado em JSON.

O formato geral do resultado inclui:

- `tool`
- `command`
- `returncode`
- `stdout`
- `stderr`

## Exemplos de consultas locais

Pesquisar um termo na base local do SearchSploit:

```bash
python pentest_tools.py searchsploit "OpenSSH"
```

Inspecionar um arquivo com Binwalk:

```bash
python pentest_tools.py binwalk caminho/do/arquivo.bin
```

Consultar informações estáticas de um binário com Radare2:

```bash
python pentest_tools.py radare2 caminho/do/arquivo
```

Consultar a versão instalada do Ettercap:

```bash
python pentest_tools.py ettercap
```

As funções do catálogo que operam sobre hosts, serviços ou credenciais exigem a confirmação explícita `authorized=True` na API Python. O modo CLI oferece a opção `--authorized` antes do nome da ferramenta. Use integrações de rede somente em ambientes próprios ou com autorização expressa.

## Dependências externas

Pentest Tools não possui um conjunto de bibliotecas Python adicional. Cada integração depende do executável correspondente estar instalado no sistema.

O catálogo não é um instalador de Nmap, Wireshark, Nikto ou dos demais programas: ele é uma camada de integração. A disponibilidade de pacotes e nomes de executáveis varia entre Termux, Debian, Ubuntu e distribuições especializadas.

---

# Executar programas individualmente

O launcher é opcional para iniciar os programas que possuem entrada própria.

Na raiz do projeto:

```bash
# Mianba
python tools/mianba.py

# Rasco OSINT
python tools/RascoOsint.py

# Jester
bash tools/jester.sh

# Pentest Tools
python pentest_tools.py --help

# Network Tools
python network_tools.py --help

# File Tools
python file_tools.py --help

# MoonScan
./tools/moonscan --help
```

---

# Adicionar ferramentas à GrasshoppeR

A arquitetura do launcher permite adicionar programas sem reescrever seu código em Python.

## Passos

1. Coloque o arquivo em `tools/` ou em uma subpasta.
2. Utilize uma extensão reconhecida.
3. Instale o runtime necessário.
4. Instale as dependências próprias do programa.
5. Reinicie a GrasshoppeR.

O launcher pesquisa ferramentas em subdiretórios e reconhece vários runtimes.

Para programas com nomes já vinculados às opções fixas do menu, mantenha o nome-base esperado pelo launcher.

---

# Testes automatizados

Os testes do projeto estão na pasta `tests/`.

Execute a suíte:

```bash
python -m unittest discover -s tests -v
```

Arquivos:

| Teste | Área |
|---|---|
| `tests/test_cli.py` | Launcher, descoberta e execução de ferramentas |
| `tests/test_files.py` | Hashes, metadados, manifestos e ZIP |
| `tests/test_network.py` | DNS, HTTP, TLS e conexões TCP em ambiente de teste |

---

# Estrutura do projeto

```text
Grasshopper-Suite/
│
├── Grasshopper.py
├── network_tools.py
├── file_tools.py
├── pentest_tools.py
├── install.sh
├── requests.txt
│
├── tests/
│   ├── test_cli.py
│   ├── test_files.py
│   └── test_network.py
│
└── tools/
    ├── jester.sh
    ├── install.sh
    ├── moonscan.go
    ├── RascoOsint.py
    ├── mianba.py
    │
    ├── core/
    │   ├── url_utils.py
    │   ├── api_detector.py
    │   └── jestercopy.py
    │
    └── tools/
        ├── extract_links.js
        ├── router.php
        ├── fastfetch.go
        └── checksum.cpp
```

---

# Tecnologias

| Tecnologia | Aplicação |
|---|---|
| Python | Launcher e módulos principais |
| Go | MoonScan e FastFetch |
| Shell / Bash | Interface e inicialização da Jester |
| JavaScript / Node.js | Extração complementar de referências |
| PHP | Pré-visualizador local |
| C++17 | Manifesto e duplicados |
| SQLite | Histórico do Rasco |
| Rich | Interface do Rasco e Mianba |
| Colorama | Cores do launcher |
| Requests | Requisições HTTP |
| Beautiful Soup | Extração HTML |
| lxml | Parser HTML/XML |

---

# Créditos e inspirações

A GrasshoppeR Suite é um projeto modular que reúne implementações próprias e integrações com programas externos.

Algumas ideias e abordagens foram inspiradas por ferramentas já conhecidas, incluindo:

- **WhatWeb:** referência conceitual para identificação de tecnologias e fingerprinting de aplicações web.
- **AliensEye:** referência de inspiração para o universo de ferramentas de reconhecimento e coleta de informações.

Essas referências não significam que os programas sejam cópias ou versões oficiais dessas ferramentas. MoonScan, Rasco, Mianba, Jester e os módulos da GrasshoppeR possuem seus próprios códigos, estruturas, interfaces e objetivos.

Ferramentas externas reconhecidas pelo Pentest Tools permanecem projetos independentes, com seus próprios autores e licenças.

---

## GrasshoppeR Suite

**Uma central. Várias ferramentas. Diferentes linguagens.**

Desenvolvida para reunir utilitários independentes em uma experiência de terminal organizada, extensível e adaptável ao Termux e Linux.
