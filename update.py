import os
import re
import sys
import json
import tempfile
import zipfile
import shutil
import stat
import urllib.request
import urllib.error
from pathlib import Path

UPSTREAM_OWNER = "Jump-On-Studios"
UPSTREAM_REPO = "RedM-jo_libs"

GITHUB_API = f"https://api.github.com/repos/{UPSTREAM_OWNER}/{UPSTREAM_REPO}"

ROOT = Path(__file__).resolve().parent
FXMANIFEST = ROOT / "fxmanifest.lua"


def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def get_current_version():
    if not FXMANIFEST.exists():
        print("ERRO: fxmanifest.lua nao encontrado")
        sys.exit(1)

    content = FXMANIFEST.read_text(encoding="utf-8")
    match = re.search(r'version\s+"([^"]+)"', content)
    if not match:
        print("ERRO: versao nao encontrada no fxmanifest.lua")
        sys.exit(1)

    return match.group(1)


def parse_version(v: str):
    parts = v.strip().split(".")
    return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])


def get_latest_upstream_version():
    url = f"{GITHUB_API}/tags?per_page=20"
    req = urllib.request.Request(url, headers={
        "User-Agent": "update.py/1.0",
        "Accept": "application/vnd.github.v3+json"
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"ERRO: falha ao buscar tags do GitHub: {e.code} {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERRO: sem conexao com GitHub: {e.reason}")
        sys.exit(1)

    version_tags = []
    for tag in tags:
        name = tag["name"].lstrip("vV")
        if re.match(r"^\d+\.\d+\.\d+", name):
            version_tags.append((parse_version(name), name, tag["name"]))

    if not version_tags:
        print("ERRO: nenhuma tag de versao encontrada no upstream")
        sys.exit(1)

    version_tags.sort(key=lambda x: x[0], reverse=True)
    return version_tags[0]


def download_and_update(latest_tag: str):
    zip_url = f"{GITHUB_API}/zipball/refs/tags/{latest_tag}"
    print(f"Baixando {UPSTREAM_OWNER}/{UPSTREAM_REPO} {latest_tag}...")

    req = urllib.request.Request(zip_url, headers={
        "User-Agent": "update.py/1.0",
        "Accept": "application/vnd.github.v3+json"
    })

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        print(f"ERRO: falha ao baixar atualizacao: {e}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "update.zip"
        zip_path.write_bytes(data)

        extract_dir = Path(tmpdir) / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if not dirs:
            print("ERRO: zip vazio ou estrutura inesperada")
            sys.exit(1)

        source_root = dirs[0]
        jo_libs_source = source_root / "jo_libs"

        if not jo_libs_source.exists() or not jo_libs_source.is_dir():
            print("ERRO: pasta 'jo_libs' nao encontrada dentro do zip do upstream")
            sys.exit(1)

        version_clean = latest_tag.lstrip("vV").replace(".", "_")
        backup_dir = ROOT / f".backup_{version_clean}"

        if backup_dir.exists():
            shutil.rmtree(backup_dir, onerror=on_rm_error)

        shutil.copytree(ROOT, backup_dir, ignore=shutil.ignore_patterns(".backup_*"))
        print(f"Backup criado em: {backup_dir}")

        for item in jo_libs_source.iterdir():
            dest = ROOT / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest, onerror=on_rm_error)
                else:
                    dest.chmod(stat.S_IWRITE)
                    dest.unlink()
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    print(f"Atualizado para versao {latest_tag}")


def main():
    current = get_current_version()
    print(f"Versao atual: {current}")

    latest_parsed, latest_raw, latest_tag = get_latest_upstream_version()
    print(f"Ultima versao upstream: {latest_raw}")

    if latest_parsed > parse_version(current):
        print(f"Nova versao disponivel: {latest_raw}")
        resposta = input("Deseja atualizar? (s/N): ").strip().lower()
        if resposta == "s":
            download_and_update(latest_tag)
        else:
            print("Atualizacao cancelada.")
    else:
        print("Voce ja esta na versao mais recente.")


if __name__ == "__main__":
    main()
