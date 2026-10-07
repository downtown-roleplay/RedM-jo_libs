"""Atualiza o jo_libs a partir do upstream SEM perder as alteracoes do fork.

Merge de 3 vias, arquivo por arquivo:
  base   = upstream no commit em que o fork foi sincronizado (SHA em .upstream-base)
  nosso  = o que esta nesta pasta
  novo   = upstream main agora

Arquivo que so o upstream mexeu e atualizado; que so nos mexemos fica como esta;
que os dois mexeram passa por `git merge-file`. Conflito fica com marcadores
<<<<<<< no arquivo e e listado no fim. Nada e escrito antes da confirmacao, e o
rollback e do proprio git (`git checkout . && git clean -fd`).

Uso:  python update.py          (mostra o plano e pergunta)
      python update.py --test   (autoteste da regra de decisao)
"""
import io
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

UPSTREAM = "Jump-On-Studios/RedM-jo_libs"
API = f"https://api.github.com/repos/{UPSTREAM}"
SUBDIR = "jo_libs/"  # pasta do resource dentro do repo upstream

ROOT = Path(__file__).resolve().parent
BASE_FILE = ROOT / ".upstream-base"

# Saida de build (bundle minificado): merge por linha nao faz sentido, upstream ganha.
UPSTREAM_WINS = ("html/dist/",)
SKIP_DIRS = {".git", ".vscode"}


def fetch(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"User-Agent": "update.py", "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except Exception as e:
        sys.exit(f"ERRO: falha ao baixar {url}: {e}")


def upstream_tree(sha):
    """{caminho relativo: bytes} da pasta jo_libs/ do upstream naquele commit."""
    files = {}
    with zipfile.ZipFile(io.BytesIO(fetch(f"{API}/zipball/{sha}"))) as zf:
        for info in zf.infolist():
            rel = info.filename.split("/", 1)[-1]  # tira a pasta raiz do zip
            if rel.startswith(SUBDIR) and not info.is_dir():
                files[rel[len(SUBDIR):]] = zf.read(info)
    if not files:
        sys.exit(f"ERRO: pasta '{SUBDIR}' nao encontrada no upstream ({sha})")
    return files


def local_tree():
    files = {}
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if path.is_file() and rel.parts[0] not in SKIP_DIRS and not rel.parts[0].startswith(".backup_"):
            files[rel.as_posix()] = path.read_bytes()
    return files


def norm(data):
    """Texto comparado sem CRLF (o git do Windows converte no checkout); binario cru."""
    if data is None or b"\0" in data:
        return data
    return data.replace(b"\r\n", b"\n")


def decide(base, ours, new):
    """Regra do merge para um arquivo. Devolve 'keep', 'take', 'merge' ou 'conflict'."""
    base, ours, new = norm(base), norm(ours), norm(new)
    if ours == new or new == base:
        return "keep"       # ja igual, ou o upstream nao mexeu
    if ours == base:
        return "take"       # nos nao mexemos: vale o upstream (inclusive remocao)
    if None in (base, ours, new):
        return "conflict"   # um lado criou/apagou e o outro alterou
    return "merge"


def merge_text(base, ours, new):
    """git merge-file. Devolve (conteudo, numero de conflitos)."""
    with tempfile.TemporaryDirectory() as tmp:
        names = []
        for name, data in (("nosso", ours), ("base", base), ("upstream", new)):
            (Path(tmp) / name).write_bytes(norm(data))
            names.append(str(Path(tmp) / name))
        proc = subprocess.run(
            ["git", "merge-file", "-p", "-L", "nosso", "-L", "base", "-L", "upstream", *names],
            capture_output=True)
    if proc.returncode < 0 or proc.returncode > 127:
        sys.exit(f"ERRO: git merge-file falhou: {proc.stderr.decode(errors='replace')}")
    return proc.stdout, proc.returncode


def plan(base, ours, new):
    """{caminho: (acao, conteudo|None)} so para o que muda no disco, + lista de avisos."""
    writes, warnings = {}, []
    for rel in sorted(set(base) | set(ours) | set(new)):
        b, o, n = base.get(rel), ours.get(rel), new.get(rel)
        action = decide(b, o, n)
        if action == "take":
            writes[rel] = ("atualizado" if n is not None else "removido", n)
        elif action == "merge":
            if rel.startswith(UPSTREAM_WINS) or b"\0" in b + o + n:
                writes[rel] = ("atualizado", n)
                warnings.append(f"{rel}: alteracao local DESCARTADA (binario/build, upstream ganha)")
            else:
                merged, conflicts = merge_text(b, o, n)
                writes[rel] = ("CONFLITO" if conflicts else "mesclado", merged)
                if conflicts:
                    warnings.append(f"{rel}: {conflicts} conflito(s), resolver os marcadores <<<<<<<")
        elif action == "conflict":
            warnings.append(f"{rel}: um lado apagou/criou e o outro alterou - mantido o nosso, conferir")
    return writes, warnings


def version(tree):
    m = re.search(rb'version\s+"([^"]+)"', tree.get("fxmanifest.lua", b""))
    return m.group(1).decode() if m else "?"


def selftest():
    a, b, c = b"a\n", b"b\n", b"c\n"
    assert decide(a, a, a) == "keep"
    assert decide(a, a, b) == "take"          # so upstream mudou
    assert decide(a, a, None) == "take"       # upstream removeu, nos nao mexemos
    assert decide(None, None, b) == "take"    # arquivo novo no upstream
    assert decide(a, b, a) == "keep"          # so nos mudamos
    assert decide(None, b, None) == "keep"    # arquivo so do fork
    assert decide(a, b, b) == "keep"          # mesma mudanca dos dois lados
    assert decide(a, b"a\r\n", b) == "take"   # CRLF local nao conta como alteracao
    assert decide(a, b, c) == "merge"
    assert decide(a, b, None) == "conflict"   # upstream removeu o que alteramos
    merged, n = merge_text(b"1\n2\n3\n", b"1\n2\n3\nnosso\n", b"upstream\n1\n2\n3\n")
    assert (merged, n) == (b"upstream\n1\n2\n3\nnosso\n", 0)
    assert merge_text(a, b, c)[1] == 1
    print("ok")


def main():
    if "--test" in sys.argv:
        return selftest()
    if not BASE_FILE.exists():
        sys.exit("ERRO: .upstream-base nao existe (SHA do upstream em que o fork foi sincronizado)")
    base_sha = BASE_FILE.read_text().strip()
    new_sha = fetch(f"{API}/commits/main", "application/vnd.github.sha").decode().strip()
    if new_sha == base_sha:
        return print("Ja esta sincronizado com o upstream main.")

    print(f"Baixando upstream: base {base_sha[:7]} e main {new_sha[:7]}...")
    base, new, ours = upstream_tree(base_sha), upstream_tree(new_sha), local_tree()
    writes, warnings = plan(base, ours, new)

    print(f"\nVersao: {version(ours)} -> {version(new)}")
    for rel, (action, _) in writes.items():
        print(f"  {action:10} {rel}")
    local = [r for r in sorted(ours) if norm(ours[r]) != norm(base.get(r))]
    print(f"\n{len(writes)} arquivo(s) mudam; {len(local)} com alteracao do fork sao mantidos/mesclados.")
    for w in warnings:
        print(f"  AVISO  {w}")

    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    if dirty.strip():
        sys.exit("\nHa alteracoes nao commitadas nesta pasta. Commite antes: o commit e o backup.")
    if input("\nAplicar? (s/N): ").strip().lower() != "s":
        return print("Cancelado.")

    for rel, (_, data) in writes.items():
        path = ROOT / rel
        if data is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    BASE_FILE.write_text(new_sha + "\n")
    print(f"Atualizado para {version(new)} ({new_sha[:7]}). Confira com `git diff` e commite"
          + (" depois de resolver os conflitos." if any(a == "CONFLITO" for a, _ in writes.values()) else "."))


if __name__ == "__main__":
    main()
