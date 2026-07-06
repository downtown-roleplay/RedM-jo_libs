import os
import re
import sys
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

# Caminho dos arquivos que NAO devem ser tocados durante a atualizacao
PRESERVE_DIR = ROOT / "modules" / "framework-bridge" / "cores" / "core"


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


def get_upstream_version_from_raw():
    """Busca a versao mais recente lendo o fxmanifest.lua raw do branch main."""
    url = "https://raw.githubusercontent.com/" \
          f"{UPSTREAM_OWNER}/{UPSTREAM_REPO}/main/jo_libs/fxmanifest.lua"
    req = urllib.request.Request(url, headers={
        "User-Agent": "update.py/1.0"
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"ERRO: falha ao buscar fxmanifest.lua upstream: {e.code} {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERRO: sem conexao com GitHub: {e.reason}")
        sys.exit(1)

    match = re.search(r'version\s+"([^"]+)"', content)
    if not match:
        print("ERRO: versao nao encontrada no fxmanifest.lua upstream")
        sys.exit(1)

    return match.group(1)


def download_and_update(upstream_version: str, create_backup: bool = True):
    version_clean = upstream_version.replace(".", "_")
    zip_url = f"{GITHUB_API}/zipball/heads/main"
    print(f"Baixando {UPSTREAM_OWNER}/{UPSTREAM_REPO} versao {upstream_version}...")

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

        # --- Backup dos arquivos preservados antes de sobrescrever ---
        preserved_temp = None
        if PRESERVE_DIR.exists() and PRESERVE_DIR.is_dir():
            preserved_temp = Path(tmpdir) / "preserved_core"
            shutil.copytree(PRESERVE_DIR, preserved_temp)
            print(f"Arquivos preservados salvos temporariamente: {PRESERVE_DIR}")

        if create_backup:
            backup_dir = ROOT / f".backup_{version_clean}"

            if backup_dir.exists():
                try:
                    shutil.rmtree(backup_dir, onerror=on_rm_error)
                except Exception as e:
                    print(f"AVISO: nao foi possivel remover backup existente: {e}")

            shutil.copytree(ROOT, backup_dir, ignore=shutil.ignore_patterns(".backup_*"))
            print(f"Backup criado em: {backup_dir}")
        else:
            print("Backup skipping (desativado pelo usuario)")

        # --- Copia todos os arquivos do upstream, item por item ---
        for item in jo_libs_source.iterdir():
            dest = ROOT / item.name
            # Se for exatamente a pasta que queremos preservar, nao deleta nem copia
            if dest == PRESERVE_DIR:
                continue

            if dest.exists():
                if dest.is_dir():
                    try:
                        shutil.rmtree(dest, onerror=on_rm_error)
                    except Exception as e:
                        print(f"AVISO: nao foi possivel remover {dest}: {e}")
                        continue
                else:
                    dest.chmod(stat.S_IWRITE)
                    dest.unlink()
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # --- Restaura os arquivos preservados por cima do que foi copiado ---
        if preserved_temp is not None:
            # Garante que o diretorio de destino existe (pode ter sido recriado pelo copytree)
            PRESERVE_DIR.mkdir(parents=True, exist_ok=True)
            for item in preserved_temp.iterdir():
                dest = PRESERVE_DIR / item.name
                if dest.exists():
                    if dest.is_dir():
                        try:
                            shutil.rmtree(dest, onerror=on_rm_error)
                        except Exception as e:
                            print(f"AVISO: nao foi possivel remover {dest}: {e}")
                            continue
                    else:
                        dest.chmod(stat.S_IWRITE)
                        dest.unlink()
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            print(f"Arquivos preservados restaurados: {PRESERVE_DIR}")

        # Atualiza o fxmanifest.lua com a nova versao
        if FXMANIFEST.exists():
            content = FXMANIFEST.read_text(encoding="utf-8")
            content = re.sub(
                r'(version\s+)"([^"]+)"',
                rf'\1"{upstream_version}"',
                content
            )
            FXMANIFEST.write_text(content, encoding="utf-8")

    print(f"Atualizado para versao {upstream_version}")


def main():
    current = get_current_version()
    print(f"Versao atual: {current}")

    upstream_version = get_upstream_version_from_raw()
    print(f"Ultima versao upstream: {upstream_version}")

    if upstream_version != current:
        print(f"Nova versao disponivel: {upstream_version}")
        resposta = input("Deseja atualizar? (s/N): ").strip().lower()
        if resposta != "s":
            print("Atualizacao cancelada.")
            return

        resposta_bkp = input("Criar backup antes de atualizar? (S/n): ").strip().lower()
        create_backup = resposta_bkp != "n"

        download_and_update(upstream_version, create_backup=create_backup)
    else:
        print("Voce ja esta na versao mais recente.")


if __name__ == "__main__":
    main()
