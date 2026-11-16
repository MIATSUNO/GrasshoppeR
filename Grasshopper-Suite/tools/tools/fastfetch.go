// fastfetch.go — acelerador em Go para a Jester
// =================================================
// Dois modos de uso (chamados pelo núcleo em Python quando o binário
// compilado está disponível; se não estiver, o Python faz tudo sozinho
// e a Jester continua funcionando 100% sem o Go):
//
//   fastfetch sitemap <http(s)://dominio> [--timeout 10]
//       Busca <base>/robots.txt (por linhas "Sitemap:") e
//       <base>/sitemap.xml / sitemap_index.xml, resolve
//       sitemaps aninhados em paralelo (goroutines) e imprime no
//       stdout, uma por linha, toda URL de página encontrada. Isso
//       ajuda a achar páginas "órfãs" que não têm link apontando pra
//       elas a partir do index — sitemap é a forma mais confiável de
//       listar TODAS as páginas de um domínio.
//
//   fastfetch fetch [--workers 16] [--timeout 15]
//       Lê do stdin linhas no formato "URL\tCAMINHO_DESTINO", baixa
//       tudo concorrentemente com um pool de goroutines e grava cada
//       arquivo no caminho indicado (criando diretórios conforme
//       necessário). Para cada URL imprime no stdout:
//           OK\t<url>\t<bytes>
//           FAIL\t<url>\t<motivo>
//       Usado pela Jester como "varredura turbo" para baixar em lote
//       (ou tentar novamente) um conjunto grande de arquivos binários
//       (imagens, vídeos, áudio, fontes) mais rápido do que uma a uma.
//
// Compilação:  go build -o fastfetch fastfetch.go
package main

import (
	"bufio"
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

const userAgent = "Jester-Cloner/1.0 (+uso-autorizado-apenas; acelerador-go)"

// ---------------------------------------------------------------- sitemap

type sitemapURL struct {
	Loc string `xml:"loc"`
}

type urlSet struct {
	URLs []sitemapURL `xml:"url"`
}

type sitemapIndex struct {
	Sitemaps []sitemapURL `xml:"sitemap"`
}

func httpGet(client *http.Client, url string) ([]byte, int, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, 0, err
	}
	req.Header.Set("User-Agent", userAgent)
	resp, err := client.Do(req)
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 50*1024*1024)) // trava de segurança: 50MB
	if err != nil {
		return nil, resp.StatusCode, err
	}
	return body, resp.StatusCode, nil
}

func findRobotsSitemaps(client *http.Client, base string) []string {
	body, status, err := httpGet(client, base+"/robots.txt")
	if err != nil || status != 200 {
		return nil
	}
	var found []string
	for _, line := range strings.Split(string(body), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(strings.ToLower(line), "sitemap:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				found = append(found, strings.TrimSpace(parts[1]))
			}
		}
	}
	return found
}

// resolveSitemap baixa uma URL de sitemap; se for um índice de sitemaps,
// resolve cada um deles em paralelo (uma goroutine por sitemap filho);
// se for um conjunto de URLs, devolve as próprias páginas.
func resolveSitemap(client *http.Client, url string, depth int, seen *sync.Map, out chan<- string, wg *sync.WaitGroup) {
	defer wg.Done()
	if depth > 4 {
		return // trava contra recursão maliciosa/infinita em sitemaps mal formados
	}
	if _, loaded := seen.LoadOrStore(url, true); loaded {
		return
	}

	body, status, err := httpGet(client, url)
	if err != nil || status != 200 || len(body) == 0 {
		return
	}

	var idx sitemapIndex
	if xml.Unmarshal(body, &idx) == nil && len(idx.Sitemaps) > 0 {
		for _, s := range idx.Sitemaps {
			if s.Loc == "" {
				continue
			}
			wg.Add(1)
			go resolveSitemap(client, s.Loc, depth+1, seen, out, wg)
		}
		return
	}

	var set urlSet
	if xml.Unmarshal(body, &set) == nil {
		for _, u := range set.URLs {
			if u.Loc != "" {
				out <- u.Loc
			}
		}
	}
}

// cmdSitemap recebe a URL-base JÁ resolvida (com esquema), ex.:
// "https://exemplo.com" ou "http://127.0.0.1:8912" — quem decide entre
// http/https é o núcleo em Python, que já testou isso ao acessar a
// página inicial; aqui não assumimos nenhum dos dois.
func cmdSitemap(base string, timeout time.Duration) {
	client := &http.Client{Timeout: timeout}
	base = strings.TrimRight(base, "/")
	candidates := []string{base + "/sitemap.xml", base + "/sitemap_index.xml"}
	candidates = append(candidates, findRobotsSitemaps(client, base)...)

	seen := &sync.Map{}
	out := make(chan string, 4096)
	var wg sync.WaitGroup

	for _, c := range candidates {
		wg.Add(1)
		go resolveSitemap(client, c, 0, seen, out, &wg)
	}

	go func() {
		wg.Wait()
		close(out)
	}()

	printed := &sync.Map{}
	for u := range out {
		if _, loaded := printed.LoadOrStore(u, true); !loaded {
			fmt.Println(u)
		}
	}
}

// ------------------------------------------------------------------ fetch

func downloadOne(client *http.Client, url, dest string) (int64, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return 0, err
	}
	req.Header.Set("User-Agent", userAgent)
	resp, err := client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return 0, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
		return 0, err
	}
	f, err := os.Create(dest)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	n, err := io.Copy(f, io.LimitReader(resp.Body, 500*1024*1024)) // trava de segurança: 500MB/arquivo
	if err != nil {
		return n, err
	}
	return n, nil
}

func cmdFetch(workers int, timeout time.Duration) {
	client := &http.Client{Timeout: timeout}
	jobs := make(chan [2]string, 256)
	var wg sync.WaitGroup
	var mu sync.Mutex // protege stdout para não intercalar linhas

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for job := range jobs {
				url, dest := job[0], job[1]
				n, err := downloadOne(client, url, dest)
				mu.Lock()
				if err != nil {
					fmt.Printf("FAIL\t%s\t%s\n", url, err.Error())
				} else {
					fmt.Printf("OK\t%s\t%d\n", url, n)
				}
				mu.Unlock()
			}
		}()
	}

	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.TrimSpace(line) == "" {
			continue
		}
		parts := strings.SplitN(line, "\t", 2)
		if len(parts) != 2 {
			continue
		}
		jobs <- [2]string{parts[0], parts[1]}
	}
	close(jobs)
	wg.Wait()
}

// ------------------------------------------------------------------- main

func parseIntFlag(args []string, name string, def int) int {
	for i, a := range args {
		if a == name && i+1 < len(args) {
			if v, err := strconv.Atoi(args[i+1]); err == nil {
				return v
			}
		}
	}
	return def
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "uso: fastfetch sitemap <http(s)://dominio> | fastfetch fetch [--workers N] [--timeout S]")
		os.Exit(2)
	}

	switch os.Args[1] {
	case "sitemap":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "uso: fastfetch sitemap <http(s)://dominio>")
			os.Exit(2)
		}
		timeout := time.Duration(parseIntFlag(os.Args, "--timeout", 10)) * time.Second
		cmdSitemap(os.Args[2], timeout)
	case "fetch":
		workers := parseIntFlag(os.Args, "--workers", 16)
		timeout := time.Duration(parseIntFlag(os.Args, "--timeout", 15)) * time.Second
		cmdFetch(workers, timeout)
	default:
		fmt.Fprintln(os.Stderr, "comando desconhecido:", os.Args[1])
		os.Exit(2)
	}
}
