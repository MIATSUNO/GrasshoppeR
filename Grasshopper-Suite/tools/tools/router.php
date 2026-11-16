<?php
/**
 * router.php — pré-visualizador local da Jester
 * ================================================
 * Serve, no próprio celular (via `php -S`), o site que acabou de ser
 * clonado — útil pra conferir rapidamente o resultado antes de levar
 * a pasta pra outro lugar. PHP entra aqui pelo seu ponto forte real:
 * o servidor embutido (`php -S`) é a forma mais rápida de subir um
 * preview estático sem instalar nada além do próprio PHP.
 *
 * A Jester salva rotas "limpas" (ex.: /sobre) como /sobre.html em
 * disco. Este roteador resolve isso na hora de servir:
 *   1. Se o caminho pedido já existe como arquivo -> deixa o servidor
 *      embutido do PHP servir direto (mime-type correto automático).
 *   2. Senão, tenta "<caminho>.html".
 *   3. Senão, se for um diretório, tenta "<caminho>/index.html".
 *   4. Senão, 404 simples.
 *
 * Uso (a partir da pasta de saída da Jester, ex. jester_output/<dominio>):
 *   php -S 0.0.0.0:8080 ../../tools/router.php
 * e depois abra http://localhost:8080/ no navegador do celular.
 */

$docroot = getcwd();
$uri = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));
$path = $docroot . $uri;

// 1) arquivo existe exatamente como pedido -> deixa o servidor embutido cuidar
if ($uri !== '/' && file_exists($path) && is_file($path)) {
    return false;
}

// 2) tenta acrescentar .html (rota "limpa" tipo /sobre -> /sobre.html)
$asHtml = rtrim($path, '/') . '.html';
if (is_file($asHtml)) {
    readfile($asHtml);
    header('Content-Type: text/html; charset=utf-8');
    return true;
}

// 3) diretório -> tenta index.html dentro dele
if (is_dir($path)) {
    $index = rtrim($path, '/') . '/index.html';
    if (is_file($index)) {
        header('Content-Type: text/html; charset=utf-8');
        readfile($index);
        return true;
    }
}

// 4) raiz sem index.html ainda
if ($uri === '/' && is_file($docroot . '/index.html')) {
    header('Content-Type: text/html; charset=utf-8');
    readfile($docroot . '/index.html');
    return true;
}

http_response_code(404);
echo "404 — não encontrado no clone: " . htmlspecialchars($uri);
return true;
