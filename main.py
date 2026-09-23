# main.py
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from src import config
from src.llm import LLMError
from src.pipeline import MIN_IDEIA, validar
from src.prompts import FASES

BANNER = "=" * 60
OUT_DIR = Path("relatorios")


def _slug(texto: str, limite: int = 60) -> str:
    """Nome de arquivo previsível: sem acento, sem pontuação, sem espaço."""
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    base = re.sub(r"[^\w\s-]", " ", base).strip().lower()
    base = re.sub(r"[\s_-]+", "-", base)
    return base[:limite].strip("-") or "ideia"


def salvar(doc: str, ideia: str, out_dir: Path = OUT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{stamp}-{_slug(ideia)}.md"
    path.write_text(doc, encoding="utf-8")
    return path


def ler_stdin() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Descreva a ideia (tipo de oferta, público, promessa, preço).")
    print("Finalize com uma linha vazia:\n")
    linhas: list[str] = []
    while True:
        try:
            linha = input()
        except (EOFError, KeyboardInterrupt):
            break
        if not linha.strip():
            if linhas:
                break
            continue
        linhas.append(linha)
    return "\n".join(linhas)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="proofkit",
        description="Valida ideias de produtos digitais com evidência.",
    )
    p.add_argument("--ideia", help="Ideia em uma linha. Omitido, lê do stdin.")
    p.add_argument("--sem-triagem", action="store_true",
                   help="Pula o corte inicial e paga todas as fases.")
    p.add_argument("--out", type=Path, default=OUT_DIR,
                   help="Pasta de destino dos relatórios.")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="Sem progresso; imprime só o caminho do relatório.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        config.api_key()
    except Exception as e:  # config define exceções próprias
        print(f"Configuração inválida: {e}", file=sys.stderr)
        return 2

    ideia = (args.ideia or ler_stdin()).strip()
    if len(ideia) < MIN_IDEIA:
        print(
            f"Ideia ausente ou vaga demais: mínimo {MIN_IDEIA} caracteres.",
            file=sys.stderr,
        )
        return 2

    if not args.quiet:
        print(BANNER, "VALIDADOR DE INFOPRODUTOS", BANNER, sep="\n")
        print(f"\nAnalisando {len(FASES)} fases...\n")

    try:
        doc, llm = validar(
            ideia, progresso=not args.quiet, triagem=not args.sem_triagem
        )
    except LLMError as e:
        print(f"\nFalha: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido antes de gerar o relatório.", file=sys.stderr)
        return 130

    try:
        path = salvar(doc, ideia, args.out)
    except OSError as e:
        # O relatório já foi pago: despeja no stdout em vez de perdê-lo.
        print(f"Não foi possível gravar em {args.out}: {e}", file=sys.stderr)
        print(doc)
        return 1

    if args.quiet:
        print(path)
    else:
        print(doc)
        print(f"\n{BANNER}\nSalvo em: {path}")
        print(f"Custo: US$ {llm.usage.cost:.4f} | Chamadas: {llm.usage.calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
