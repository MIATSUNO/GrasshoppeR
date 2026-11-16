// checksum.cpp — verificador de integridade/duplicados da Jester
// ===================================================================
// Depois que a Jester termina de clonar um site, este utilitário varre
// toda a pasta de saída, calcula um hash (FNV-1a 64 bits) de cada
// arquivo e gera:
//   manifesto.tsv    -> hash<TAB>tamanho_em_bytes<TAB>caminho_relativo
//   duplicados.txt   -> grupos de arquivos com conteúdo idêntico
//                       (ex.: o mesmo logo.png referenciado e salvo
//                       várias vezes por páginas diferentes)
//
// É C++ puro (std::filesystem, C++17), sem dependências externas — só
// precisa de g++/clang++. Totalmente opcional: se não for compilado
// no Termux (toolchain `clang` ausente), a Jester funciona normalmente
// sem esse relatório extra.
//
// Uso:   checksum <diretorio_de_saida>
// Compilação:  g++ -std=c++17 -O2 -o checksum checksum.cpp

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

// FNV-1a 64 bits — rápido, determinístico, suficiente para detectar
// duplicatas e checar integridade (não é destinado a uso criptográfico).
static uint64_t fnv1a64(const std::vector<char> &data) {
    uint64_t hash = 14695981039346656037ULL;
    const uint64_t prime = 1099511628211ULL;
    for (unsigned char c : data) {
        hash ^= c;
        hash *= prime;
    }
    return hash;
}

static bool readFile(const fs::path &p, std::vector<char> &out) {
    std::ifstream in(p, std::ios::binary | std::ios::ate);
    if (!in) return false;
    std::streamsize size = in.tellg();
    if (size < 0) return false;
    in.seekg(0, std::ios::beg);
    out.resize(static_cast<size_t>(size));
    if (size > 0 && !in.read(out.data(), size)) return false;
    return true;
}

static std::string hex64(uint64_t v) {
    std::ostringstream oss;
    oss << std::hex << std::setw(16) << std::setfill('0') << v;
    return oss.str();
}

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "uso: checksum <diretorio_de_saida>\n";
        return 2;
    }
    fs::path root(argv[1]);
    if (!fs::exists(root) || !fs::is_directory(root)) {
        std::cerr << "diretorio invalido: " << root << "\n";
        return 2;
    }

    std::ofstream manifest(root / "manifesto.tsv", std::ios::binary);
    manifest << "# hash_fnv1a64\ttamanho_bytes\tcaminho_relativo\n";

    std::map<std::string, std::vector<std::string>> byHash;
    size_t totalFiles = 0, totalBytes = 0, errors = 0;

    for (auto it = fs::recursive_directory_iterator(
             root, fs::directory_options::skip_permission_denied);
         it != fs::recursive_directory_iterator(); ++it) {
        if (!it->is_regular_file()) continue;
        const fs::path &p = it->path();
        std::string name = p.filename().string();
        if (name == "manifesto.tsv" || name == "duplicados.txt") continue;

        std::vector<char> data;
        if (!readFile(p, data)) {
            std::cerr << "  [erro ao ler] " << p << "\n";
            errors++;
            continue;
        }
        uint64_t h = fnv1a64(data);
        std::string hashHex = hex64(h);
        std::string rel = fs::relative(p, root).generic_string();

        manifest << hashHex << "\t" << data.size() << "\t" << rel << "\n";
        byHash[hashHex].push_back(rel);

        totalFiles++;
        totalBytes += data.size();
    }
    manifest.close();

    std::ofstream dup(root / "duplicados.txt", std::ios::binary);
    size_t dupGroups = 0;
    for (auto &kv : byHash) {
        if (kv.second.size() > 1) {
            dupGroups++;
            dup << "# hash " << kv.first << " (" << kv.second.size() << " copias identicas)\n";
            for (auto &path : kv.second) dup << "  " << path << "\n";
            dup << "\n";
        }
    }
    dup.close();

    std::cout << "[checksum] Arquivos verificados: " << totalFiles << "\n";
    std::cout << "[checksum] Tamanho total ......: " << (totalBytes / 1024.0 / 1024.0)
              << " MB\n";
    std::cout << "[checksum] Grupos duplicados ..: " << dupGroups << "\n";
    std::cout << "[checksum] Falhas de leitura ..: " << errors << "\n";
    std::cout << "[checksum] Relatorios gravados em manifesto.tsv e duplicados.txt\n";
    return 0;
}
