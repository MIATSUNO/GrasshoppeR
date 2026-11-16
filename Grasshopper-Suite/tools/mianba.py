#!/usr/bin/env python3
# MIANBA - Termux/mobile edition. Recriado a partir do código fornecido.
# Uso responsável: teste somente sistemas que você possui ou está autorizado a avaliar.
import sys, os, re, time, socket, ipaddress, shutil, subprocess, select
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit
try:
    import requests
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.markup import escape
except ImportError as exc:
    print('Dependência ausente:', exc.name)
    print('Termux: pkg install python && python -m pip install requests rich')
    sys.exit(1)
try:
    import termios, tty
except ImportError:
    termios = tty = None

console = Console()
CY, BLUE, GREEN, MUTED, RED = '#39d9d0', '#41a8c7', '#8dd5c2', '#8b9da7', '#ff6b6b'
ITEMS = [
    ('01','Meu IP','IP público, provedor e localização'),
    ('02','Consultar IP / domínio','DNS reverso e localização aproximada'),
    ('03','Traceroute','Caminho de rede e saltos'),
    ('04','Scanner de portas','Portas TCP de alvos autorizados'),
    ('05','Consulta DNS','A, AAAA, MX, NS, TXT, CNAME e SOA'),
    ('06','WHOIS','Dados públicos de registro'),
    ('07','Interfaces','Endereços e rotas locais'),
    ('00','Sair','Encerrar a sessão'),
]
SERVICES = {21:'FTP',22:'SSH',23:'Telnet',25:'SMTP',53:'DNS',80:'HTTP',110:'POP3',111:'RPC',135:'MSRPC',139:'NetBIOS',143:'IMAP',443:'HTTPS',445:'SMB',465:'SMTPS',587:'SMTP/TLS',631:'IPP',993:'IMAPS',995:'POP3S',1080:'SOCKS',1194:'OpenVPN',1433:'MSSQL',1521:'Oracle',1723:'PPTP',2049:'NFS',2181:'ZooKeeper',3306:'MySQL',3389:'RDP',4444:'Possível serviço',5432:'PostgreSQL',5900:'VNC',5985:'WinRM',6379:'Redis',6667:'IRC',7001:'WebLogic',8080:'HTTP alternativo',8443:'HTTPS alternativo',8888:'Jupyter',9090:'Cockpit',9200:'Elasticsearch',9300:'Elasticsearch',11211:'Memcached',27017:'MongoDB',27018:'MongoDB',50000:'SAP'}


def clean(value):
    return escape(str(value if value is not None else '—'))


def heading(title):
    console.print(Panel(f'[bold {CY}]{clean(title)}[/]', border_style=BLUE, padding=(0,1)))


def report(pairs, title):
    t = Table(show_header=False, box=None, expand=True, padding=(0,1))
    t.add_column('Campo', style=f'bold {CY}', ratio=1, no_wrap=False)
    t.add_column('Valor', ratio=2, overflow='fold')
    for k, v in pairs:
        t.add_row(clean(k), clean(v))
    console.print(Panel(t, title=clean(title), border_style=BLUE, expand=True, padding=(0,0)))


def prompt(label):
    return console.input(f'  [bold {CY}]{escape(label)}[/] › ').strip()


def target_input(label='IP ou domínio'):
    text = prompt(label)
    if not text:
        return None
    if '://' in text:
        text = urlsplit(text).hostname or ''
    text = text.strip().rstrip('.')
    if not text or len(text) > 253 or text.startswith('-') or any(c.isspace() for c in text):
        raise ValueError('Alvo inválido.')
    try:
        ipaddress.ip_address(text)
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', text):
            raise ValueError('Use um domínio ou IP válido.')
    return text


def get_ip():
    for url in ('https://api.ipify.org?format=json','https://api64.ipify.org?format=json'):
        try:
            r = requests.get(url, timeout=5); r.raise_for_status()
            ip = r.json().get('ip'); ipaddress.ip_address(ip); return ip
        except (requests.RequestException, ValueError, TypeError):
            pass
    return None


def local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8',80)); return s.getsockname()[0]
    except OSError:
        return 'Indisponível'


def resolve(host):
    try:
        return socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)[0][4][0]
    except (OSError, IndexError):
        return None


def rdns(ip):
    try: return socket.gethostbyaddr(ip)[0]
    except OSError: return 'Sem registro PTR ou indisponível'


def geo(ip):
    # Serviço de terceiro via HTTPS. A consulta compartilha o IP consultado.
    try:
        r = requests.get('https://ipwho.is/' + ip, timeout=8); r.raise_for_status()
        data = r.json()
        return data if data.get('success') else None
    except (requests.RequestException, ValueError): return None


def geo_pairs(info):
    if not info: return [('Geolocalização','Indisponível')]
    con = info.get('connection') or {}
    return [('País',info.get('country')),('Região',info.get('region')),
            ('Cidade',info.get('city')),('Provedor',con.get('isp')),
            ('Organização',con.get('org')),('ASN',con.get('asn')),
            ('Coordenadas',f"{info.get('latitude', '—')}, {info.get('longitude', '—')}")]


def mod_myip():
    heading('MEU IP')
    console.print(f'[{MUTED}]Consultando serviços externos via HTTPS…[/]')
    ip = get_ip()
    pairs = [('IP público',ip or 'Indisponível'),('IP local',local_ip()),('Hostname',socket.gethostname())]
    if ip: pairs += geo_pairs(geo(ip))
    report(pairs, 'Perfil de rede')
    console.print(f'[{MUTED}]Localização aproximada; IP enviado ao serviço de consulta.[/]')


def mod_lookup():
    heading('CONSULTAR IP / DOMÍNIO')
    host = target_input()
    if not host: return
    ip = resolve(host)
    if not ip: print('Não foi possível resolver o alvo.'); return
    report([('Consulta',host),('IP',ip),('DNS reverso',rdns(ip))] + geo_pairs(geo(ip)), 'Resultado')
    console.print(f'[{MUTED}]Localização aproximada; IP enviado ao serviço de consulta.[/]')


def run_command(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', timeout=timeout)
        return p.returncode, p.stdout
    except FileNotFoundError: return None, ''
    except subprocess.TimeoutExpired: return -1, 'Tempo limite excedido.'


def mod_trace():
    heading('TRACEROUTE')
    host = target_input()
    if not host: return
    command = ['tracert','-d','-h','20',host] if os.name == 'nt' else ['traceroute','-n','-m','20','-w','1','-q','1',host]
    print('Consultando rota (isso pode levar alguns segundos)…')
    status, output = run_command(command, 40)
    if status is None:
        print('Traceroute não encontrado. No Termux: pkg install traceroute'); return
    console.print(Panel(clean(output.strip() or 'Sem resposta.'), title='Saltos', border_style=BLUE))
    if status != 0: print('A consulta não terminou com sucesso; verifique rede e permissões.')
    print('Um salto sem resposta não significa necessariamente falha ou destino alcançado.')


def parse_ports(scope):
    if not scope or scope == 'top': return sorted(SERVICES)
    if scope == 'top1000': return list(range(1,1001))
    ports = set()
    for part in scope.split(','):
        part = part.strip()
        if re.fullmatch(r'\d+', part): a = b = int(part)
        elif re.fullmatch(r'\d+-\d+', part): a,b = map(int, part.split('-'))
        else: raise ValueError('Formato de portas inválido.')
        if not 1 <= a <= b <= 65535: raise ValueError('Use portas entre 1 e 65535.')
        if b-a > 4095 or len(ports) + b-a+1 > 4096: raise ValueError('Limite: 4096 portas por consulta.')
        ports.update(range(a,b+1))
    if not ports: raise ValueError('Informe ao menos uma porta.')
    return sorted(ports)


def tcp(ip, port):
    try:
        with socket.create_connection((ip, port), timeout=1): return port, True
    except OSError: return port, False


def mod_scan():
    heading('SCANNER TCP')
    print('Use apenas em sistemas próprios ou com autorização explícita.')
    host = target_input()
    if not host: return
    scope = prompt('Portas: top, top1000, 80,443 ou 1-100 [top]').lower()
    ports = parse_ports(scope)
    if prompt('Você possui autorização para este alvo? [s/N]').lower() not in ('s','sim'): print('Consulta cancelada.'); return
    ip = resolve(host)
    if not ip: print('Não foi possível resolver o alvo.'); return
    print(f'Consultando {len(ports)} portas em {ip}…')
    found = []
    with ThreadPoolExecutor(max_workers=32) as ex:
        futures = [ex.submit(tcp,ip,p) for p in ports]
        for f in as_completed(futures):
            p, ok = f.result()
            if ok: found.append(p)
    report([(str(p),SERVICES.get(p,'Serviço não identificado') + ' (nome provável)') for p in sorted(found)] or [('Resultado','Nenhuma porta aberta detectada')], 'Portas TCP')
    print('Porta aberta não comprova qual serviço está rodando nem uma vulnerabilidade.')


def mod_dns():
    heading('CONSULTA DNS')
    host = target_input('Domínio')
    if not host: return
    dig = shutil.which('dig')
    ns = shutil.which('nslookup')
    if not dig and not ns:
        print('Instale as ferramentas DNS no Termux: pkg install dnsutils'); return
    pairs = []
    for typ in ('A','AAAA','MX','NS','TXT','CNAME','SOA'):
        cmd = [dig,'+short','+time=3','+tries=1',typ,host] if dig else [ns, '-type='+typ, host]
        status, result = run_command(cmd, 8)
        if status == 0 and result.strip(): pairs.append((typ,result.strip()))
        elif status != 0: pairs.append((typ,'Consulta sem resposta ou falhou'))
    report(pairs or [('Resultado','Nenhum registro retornado')], 'Registros DNS')


def mod_whois():
    heading('WHOIS')
    host = target_input('Domínio ou IP')
    if not host: return
    code, out = run_command(['whois',host],20)
    if code is None: print('WHOIS não encontrado. No Termux: pkg install whois'); return
    console.print(Panel(clean(out.strip() or 'Sem resultado.'), title='WHOIS', border_style=BLUE))
    if code != 0: print('Consulta incompleta ou falhou.')


def mod_netinfo():
    heading('INTERFACES E ROTAS')
    commands = ([['ipconfig','/all'],['route','print']] if os.name == 'nt' else [['ip','addr'],['ip','route']])
    any_ok = False
    for cmd in commands:
        code, out = run_command(cmd,8)
        if code == 0 and out.strip():
            any_ok = True
            console.print(Panel(clean(out.strip()), title=clean(' '.join(cmd)), border_style=BLUE))
        elif code is not None and out.strip():
            console.print(Panel(clean(out.strip()), title='Informação / restrição', border_style=MUTED))
    if not any_ok:
        print('Interfaces ou rotas indisponíveis. No Termux: pkg install iproute2')
        print('O Android pode restringir essas informações mesmo com o comando instalado.')


DISPATCH = {'01':mod_myip,'02':mod_lookup,'03':mod_trace,'04':mod_scan,'05':mod_dns,'06':mod_whois,'07':mod_netinfo}


def draw_menu(selected, top, number=''):
    size = shutil.get_terminal_size((80,24)); width, height = size.columns, size.lines
    console.clear()
    if width >= 51 and height >= 17:
        console.print(f'''[bold {CY}]
        ```

@@@@@@@@@@   @@@   @@@@@@@@   @@@  @@@  @@@@@@@    @@@@@@@@      @@@
@@@@@@@@@@@  @@@  @@@@@@@@@@  @@@@ @@@  @@@@@@@@  @@@@@@@@@@       @@@
@@! @@! @@!  @@!  @@!    @@@  @@!@!@@@  @@!  @@@  @@!    @@@         @@!
!@! !@! !@!  !@!  !@! @!@!!@  !@!!@!@!  !@   @!@  !@! @!@!!@           !@!
@!! !!@ @!@  !!@  @!@ !@@!@!  @!@ !!@!  @!@!@!@   @!@ !@@!@!             !!@
!@!   ! !@!  !!!  !@! @@!@!!  !@!  !!!  !!!@!!!!  !@! @@!@!!             !!!
!!:     !!:  !!:  !!:  !:!!   !!:  !!!  !!:  !!!  !!:  !:!!            !!:
:!:     :!:  :!:  :!:         :!:  !:!  :!:  !:!  :!:                :!:
:::     ::    ::  ::::::::::   ::   ::   :: ::::  ::::::::::       ::         :::::::::::::
 :      :    :     : : :: :   ::    :   :: : ::    : : :: :      :            :::::::::::::
```
        
        
        [/]''')
        console.print(f'[{BLUE}]  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]')
    else:
        console.print(f'''[bold {CY}] MIANBA[/] [{MUTED}]• NETWORK[/]''')
    console.print(f'[{MUTED}] ↑↓ mover  •  Enter abrir  •  0-7  •  q sair[/]')
    # One output line per entry; menu scrolls on short displays.
    visible = max(1, height - (6 if width >= 51 and height >= 17 else 5))
    visible = min(visible, len(ITEMS))
    top = min(top, max(0, len(ITEMS)-visible))
    if selected < top: top = selected
    if selected >= top + visible: top = selected - visible + 1
    if top: console.print(f'[{MUTED}]  ↑ mais opções[/]')
    for i in range(top, min(top+visible,len(ITEMS))):
        code,name,desc = ITEMS[i]
        chosen = i == selected
        prefix = ' ❯ ' if chosen else '   '
        style = f'bold {CY}' if chosen else 'white'
        text = Text(prefix + code + '  ' + name, style=style, no_wrap=True, overflow='ellipsis')
        if width >= 62: text.append('  ·  ' + desc, style=MUTED)
        console.print(text, crop=True, soft_wrap=False)
    if top+visible < len(ITEMS): console.print(f'[{MUTED}]  ↓ mais opções[/]')
    if number: console.print(f'[{MUTED}] Número: {escape(number)}  (Enter confirma)[/]')
    return top


def read_key(fd):
    # Recognize common CSI and application-mode sequences; do not block on bare ESC.
    ch = os.read(fd,1)
    if not ch: return 'EOF'
    if ch == b'\x03': return 'CTRL_C'
    if ch in (b'\r',b'\n'): return 'ENTER'
    if ch == b'\x1b':
        seq = b''; deadline = time.monotonic()+0.12
        while time.monotonic() < deadline and len(seq) < 12:
            ready,_,_ = select.select([fd],[],[], max(0,deadline-time.monotonic()))
            if not ready: break
            x = os.read(fd,1)
            if not x: break
            seq += x
            if x in b'ABCD~': break
        if seq in (b'[A',b'OA'): return 'UP'
        if seq in (b'[B',b'OB'): return 'DOWN'
        return 'ESC'
    try: return ch.decode('ascii').lower()
    except UnicodeDecodeError: return ''


def arrow_menu():
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    selected = 0; top = 0; number = ''; old_size = None; dirty = True
    try:
        tty.setcbreak(fd)
        while True:
            size = shutil.get_terminal_size((80,24))
            if dirty or size != old_size:
                top = draw_menu(selected,top,number); old_size = size; dirty = False
            ready,_,_ = select.select([fd],[],[],0.15)
            if not ready: continue
            key = read_key(fd)
            if key in ('CTRL_C','EOF','q'): return '00'
            if key in ('UP','k','w'):
                selected = (selected-1) % len(ITEMS); number=''; dirty=True
            elif key in ('DOWN','j','s'):
                selected = (selected+1) % len(ITEMS); number=''; dirty=True
            elif key in tuple('01234567'):
                selected = next(i for i,item in enumerate(ITEMS) if int(item[0]) == int(key))
                number = key; dirty=True
            elif key == 'ENTER': return ITEMS[selected][0]
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,saved)


def numeric_menu():
    console.print(f'\n[bold {CY}]MIANBA • MENU[/]')
    for code,name,desc in ITEMS: console.print(f'  {code}  {name}  [{MUTED}]{desc}[/]')
    try: choice = prompt('Opção (0–7) ou q').lower()
    except (EOFError, KeyboardInterrupt): return '00'
    if choice in ('q','quit','exit'): return '00'
    if choice.isdigit() and 0 <= int(choice) <= 7: return f'{int(choice):02d}'
    print('Opção inválida.'); return None


def main():
    is_tty = bool(termios and tty and sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb')
    while True:
        try:
            choice = arrow_menu() if is_tty else numeric_menu()
            if choice == '00': break
            if choice not in DISPATCH: continue
            if is_tty: console.clear()
            try: DISPATCH[choice]()
            except KeyboardInterrupt: print('\nOperação cancelada.')
            except (OSError, ValueError) as exc: print(f'Erro: {exc}')
            try: input('\nEnter para voltar ao menu… ')
            except (EOFError, KeyboardInterrupt): break
        except (EOFError,KeyboardInterrupt): break
    print('\nSessão encerrada.')

if __name__ == '__main__': main()
