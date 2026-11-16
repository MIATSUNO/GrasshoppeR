#!/usr/bin/env node
/**
 * extract_links.js — varredura extra de JavaScript para a Jester
 * ==================================================================
 * Node entra aqui pelo seu ponto forte óbvio: é quem melhor "entende"
 * a sintaxe de JavaScript. Sem precisar de nenhum pacote externo (zero
 * dependências — funciona assim que `pkg install nodejs` é feito no
 * Termux), este script varre um arquivo .js/.mjs em busca de:
 *
 *   - import ... from '...'  /  require('...')  /  import('...')
 *   - new URL('...', import.meta.url)   (padrão comum em bundlers modernos)
 *   - //# sourceMappingURL=arquivo.js.map   (revela o .map, que às vezes
 *     expõe os fontes originais e mais referências de assets)
 *   - qualquer string entre aspas que pareça caminho de arquivo com
 *     extensão de asset (imagem, vídeo, áudio, fonte, css, json, etc.)
 *
 * Uso:
 *   node extract_links.js caminho/para/arquivo.js
 *   cat arquivo.js | node extract_links.js -
 *
 * Saída: um array JSON de strings (caminhos/URLs encontrados) no stdout.
 * Chamado pelo núcleo em Python (core/jester.py) de forma OPCIONAL — se
 * o Node não estiver instalado ou o script falhar, o Python já faz essa
 * extração sozinho (com um regex mais simples) e a Jester continua
 * funcionando sem perder nada essencial.
 */

const fs = require("fs");

function readInput() {
  const arg = process.argv[2];
  if (!arg || arg === "-") {
    return fs.readFileSync(0, "utf8");
  }
  return fs.readFileSync(arg, "utf8");
}

const ASSET_EXT =
  "(?:js|mjs|cjs|css|json|txt|xml|csv|png|jpe?g|gif|webp|svg|ico|bmp|avif|" +
  "mp4|webm|mov|avi|mkv|mp3|wav|ogg|m4a|flac|woff2?|ttf|otf|eot|pdf|zip)";

const PATTERNS = [
  // import ... from '...'  /  export ... from '...'
  /\b(?:import|export)\s[^;'"]*?from\s*['"]([^'"]+)['"]/g,
  // import('...')  (import dinâmico)
  /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g,
  // require('...')
  /\brequire\(\s*['"]([^'"]+)['"]\s*\)/g,
  // new URL('...', import.meta.url) ou new URL('...', base)
  /\bnew\s+URL\(\s*['"]([^'"]+)['"]/g,
  // qualquer string com extensão de asset reconhecida
  new RegExp(`['"]([^'"]{2,300}\\.${ASSET_EXT})(?:[?#][^'"]*)?['"]`, "gi"),
];

function extractSourceMap(text) {
  const m = text.match(/\/\/[#@]\s*sourceMappingURL=([^\s'"]+)/);
  return m ? [m[1]] : [];
}

function main() {
  let text;
  try {
    text = readInput();
  } catch (err) {
    console.log("[]");
    process.exit(0); // falha silenciosa — Python usa o próprio fallback
  }

  const found = new Set();
  for (const re of PATTERNS) {
    let m;
    re.lastIndex = 0;
    while ((m = re.exec(text)) !== null) {
      const val = (m[1] || "").trim();
      if (val && !val.startsWith("data:")) {
        found.add(val);
      }
    }
  }
  for (const sm of extractSourceMap(text)) found.add(sm);

  console.log(JSON.stringify(Array.from(found)));
}

main();
