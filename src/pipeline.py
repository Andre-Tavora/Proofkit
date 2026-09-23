# src/pipeline.py
# Salve este arquivo como UTF-8 (sem BOM).
from __future__ import annotations

import re
from datetime import datetime

from . import config, evidencias, funil as funil_mod
from .fontes import Fonte
from .llm import LLM, LLMError, NoEvidenceError
from .mercado import ExcessoDeFatores, Funil, checar_breakeven
from .pendencias import Nivel, RegistroPendencias, parse_pendencias
from .prompts import (
    CONTRATO_AVALIACAO,
    FASES,
    FASE_MERCADO,
    FASE_TMPL,
    FASE_VIABILIDADE,
    RELATORIO_TMPL,
    TRIAGEM_TMPL,
    ids_str,
    system_blocks,
)
from .rubrica import Rubrica, parse_notas, rotulo_para

TOTAL = len(FASES)
AUDITORIA = "Auditoria Interna"
TENTATIVAS_CONTRATO = 2
RUBRICA = Rubrica()
MIN_IDEIA = 15

RE_FINAL = re.compile(r"score[_\s]*final[^\d]{0,20}(\d{1,3})", re.I)
RE_TRIAGEM = re.compile(r"^\s*TRIAGEM\s*:\s*(\d{1,2}(?:[.,]\d+)?)", re.I)


class OrcamentoExcedido(LLMError):
    """Gasto passou do teto antes de terminar. Interrompe em vez de sangrar."""


def _fases() -> list[tuple[str, str, bool]]:
    """Valida o contrato de FASES. O flag usa_web é obrigatório: um default
    silencioso faria uma fase de mercado passar como análise sem ter buscado."""
    out: list[tuple[str, str, bool]] = []
    for i, item in enumerate(FASES):
        if not isinstance(item, tuple) or len(item) != 3:
            n = len(item) if isinstance(item, tuple) else type(item).__name__
            raise LLMError(
                f"FASES[{i}] deve ser (titulo, instrucao, usa_web); recebi {n}."
            )
        titulo, instrucao, web = item
        if not isinstance(web, bool):
            raise LLMError(f"FASES[{i}].usa_web não é bool: {web!r}")
        out.append((str(titulo), str(instrucao), web))
    if not out:
        raise LLMError("FASES está vazio.")
    return out


def _contexto(blocos: list[tuple[str, str]]) -> str:
    if not blocos:
        return "(primeira fase — sem contexto anterior)"
    return "\n\n".join(f"## {t}\n{c}" for t, c in blocos)


def _checa_orcamento(llm: LLM, etapa: str) -> None:
    if llm.usage.cost > config.ORCAMENTO_MAX:
        raise OrcamentoExcedido(
            f"US$ {llm.usage.cost:.4f} gastos em {etapa}, teto é "
            f"US$ {config.ORCAMENTO_MAX:.2f}. Aumente VALIDADOR_ORCAMENTO ou "
            f"reduza VALIDADOR_MAX_WEB."
        )


def _extrair_avaliacao(
    texto: str,
) -> tuple[dict[str, float], RegistroPendencias, str]:
    """(notas, pendências, relatório_limpo). Levanta ValueError se violar."""
    notas, resto = parse_notas(texto)
    registro, relatorio = parse_pendencias(resto)
    return notas, registro, relatorio


# ── Funil ──────────────────────────────────────────────────────────────────
def _montar_funil(
    blocos: list[tuple[str, str]],
    registro: RegistroPendencias,
    citadas: list[Fonte],
    progresso: bool,
) -> tuple[Funil | None, str]:
    """Constrói o funil a partir do bloco FUNIL: da fase de mercado.

    Falha de parse é pendência, não exceção: o relatório já foi pago e um
    funil ausente é informação sobre o relatório, não motivo para descartá-lo.
    """
    texto = next((c for t, c in blocos if t == FASE_MERCADO), "")
    if not texto:
        return None, ""

    try:
        f, fonte = funil_mod.parse(texto)
    except ExcessoDeFatores as e:
        registro.add(
            fase=f"2. {FASE_MERCADO}",
            descricao=f"funil rejeitado — {e}",
            nivel=Nivel.ALTA,
            como_obter="agregar fatores ou verificar cada um com fonte",
        )
        return None, ""
    except funil_mod.FunilInvalido as e:
        registro.add(
            fase=f"2. {FASE_MERCADO}",
            descricao=(
                f"sem funil TAM/SAM/SOM auditável ({e}); o tamanho de mercado "
                "não pôde ser recalculado pelo sistema"
            ),
            nivel=Nivel.ALTA,
            como_obter="reexecutar a fase respeitando o bloco FUNIL:",
        )
        return None, ""

    if fonte is not None:
        citadas.append(fonte)

    final = f.final
    if not final.confiavel:
        registro.add(
            fase=f"2. {FASE_MERCADO}",
            descricao=(
                f"amplitude do funil é {final.amplitude:.1f}x (limite 3x): a "
                "faixa é larga demais para sustentar decisão de investimento"
            ),
            nivel=Nivel.ALTA,
            como_obter="verificar com fonte os fatores marcados como ESTIMATIVA",
        )
    chutes = sum(e.estimados for e in f.etapas)
    if chutes >= 3:
        registro.add(
            fase=f"2. {FASE_MERCADO}",
            descricao=f"{chutes} fatores do funil são estimativa sem fonte",
            nivel=Nivel.MEDIA,
            como_obter="benchmark de mercado ou dado primário por fator",
        )

    md = f.markdown()

    # Break-even contra o cenário pessimista, não contra o base.
    via = next((c for t, c in blocos if t == FASE_VIABILIDADE), "")
    be = funil_mod.breakeven(via) if via else None
    if be is None:
        registro.add(
            fase=f"5. {FASE_VIABILIDADE}",
            descricao="ponto de equilíbrio não declarado em número de vendas",
            nivel=Nivel.ALTA,
            como_obter="custo total ÷ margem por venda, declarado como BREAKEVEN:",
        )
    else:
        veredicto_be = checar_breakeven(be, final)
        md += f"\n### Ponto de equilíbrio\n\n{veredicto_be}\n"
        if be > final.base:
            registro.add(
                fase=f"5. {FASE_VIABILIDADE}",
                descricao=(
                    f"break-even de {be} vendas está acima do cenário base do "
                    f"funil ({final.base:,.0f})".replace(",", ".")
                ),
                nivel=Nivel.BLOQUEANTE if be > final.otimista else Nivel.ALTA,
                como_obter="reduzir custo, elevar ticket ou ampliar o universo",
            )
        elif be > final.pessimista:
            registro.add(
                fase=f"5. {FASE_VIABILIDADE}",
                descricao=(
                    f"break-even de {be} vendas exige desempenho acima do "
                    f"cenário pessimista ({final.pessimista:,.0f})".replace(",", ".")
                ),
                nivel=Nivel.MEDIA,
                como_obter="testar conversão real em campanha pequena",
            )

    if progresso:
        print(
            f"      funil: {len(f.etapas)} etapas, amplitude "
            f"{final.amplitude:.1f}x"
            + (f", break-even {be}" if be else ", break-even ausente"),
            flush=True,
        )
    return f, md


# ── Triagem ────────────────────────────────────────────────────────────────
def _triagem(llm: LLM, ideia: str, progresso: bool) -> tuple[float | None, str]:
    """Roda o corte inicial no modelo barato. Devolve (nota, texto).

    Nota None significa que o modelo não respeitou o formato — nesse caso
    seguimos para o pipeline completo em vez de reprovar por falha nossa.
    """
    texto = llm.complete(
        system_blocks(False, com_rubrica=False),
        TRIAGEM_TMPL.format(ideia=ideia),
        rotulo="triagem",
        modelo=config.MODEL_TRIAGEM,
        max_tokens=config.MAX_TOKENS_TRIAGEM,
    ).strip()

    m = RE_TRIAGEM.match(texto)
    if not m:
        if progresso:
            print("      ⚠ triagem sem nota — seguindo para o pipeline", flush=True)
        return None, texto

    nota = float(m.group(1).replace(",", "."))
    corpo = texto[m.end():].lstrip("\n")
    if progresso:
        print(f"      nota de clareza {nota:g} (corte {config.TRIAGEM_CORTE / 10:g})",
              flush=True)
    return nota, corpo


def _doc_triagem(ideia: str, nota: float, corpo: str, llm: LLM) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    return (
        "# Validação de Infoproduto — reprovado na triagem\n\n"
        f"**Ideia:** {ideia}\n\n"
        f"**Data:** {agora}  \n**Modelo de triagem:** {config.MODEL_TRIAGEM}  \n"
        f"**Custo:** US$ {llm.usage.cost:.4f}\n\n"
        f"**Veredicto:** REPROVADO NA TRIAGEM  \n"
        f"**Nota de clareza:** {nota:g}/10 "
        f"(mínimo {config.TRIAGEM_CORTE / 10:g})\n\n"
        "> A oferta não passou do primeiro critério: sem público, dor ou "
        "resultado identificáveis, as fases seguintes produziriam análise de "
        "mercado sobre uma hipótese que ainda não existe. O pipeline completo "
        "não foi executado — e não foi cobrado.\n\n"
        "---\n\n"
        f"# Diagnóstico\n\n{corpo}\n\n"
        "---\n\n"
        "# Próximo passo\n\n"
        "Reescreva a ideia respondendo, em uma frase: **quem** tem **qual dor** "
        "e **o que muda** depois de comprar. Com isso definido, rode a validação "
        "de novo.\n\n"
        f"---\n\n# Consumo\n\n```\n{llm.usage.breakdown()}\n```\n"
    )


# ────────────────────────────────────────────────────────────────────────────
def validar(
    ideia: str,
    llm: LLM | None = None,
    progresso: bool = True,
    triagem: bool = True,
) -> tuple[str, LLM]:
    """Roda triagem e fases sequencialmente; devolve (documento_markdown, llm).

    `llm` é injetável: os testes passam um dublê e o pipeline não toca disco
    nem rede. Omitido, instancia o client real.
    """
    ideia = (ideia or "").strip()
    if len(ideia) < MIN_IDEIA:
        raise LLMError(f"descreva a ideia com ao menos {MIN_IDEIA} caracteres.")

    llm = llm or LLM()
    fases = _fases()
    blocos: list[tuple[str, str]] = []
    fontes: list[str] = []
    citadas: list[Fonte] = []
    registro = RegistroPendencias()

    if triagem:
        if progresso:
            print(f"[0/{TOTAL}] Triagem ({config.MODEL_TRIAGEM})...", flush=True)
        nota, corpo = _triagem(llm, ideia, progresso)
        # O corte é em escala 0–100 para casar com as faixas de veredicto.
        if nota is not None and nota * 10 < config.TRIAGEM_CORTE:
            return _doc_triagem(ideia, nota, corpo, llm), llm

    for i, (titulo, instrucao, web) in enumerate(fases, 1):
        _checa_orcamento(llm, f"antes da fase {i}")
        ctx = _contexto(blocos)

        # A auditoria precisa ler as fases como material de TERCEIRO,
        # senão revisa o próprio texto com complacência e se autoabsolve.
        if titulo == AUDITORIA:
            ctx = (
                "MATERIAL PRODUZIDO POR OUTRO ANALISTA — audite criticamente.\n"
                "Você NÃO é o autor deste texto e não tem compromisso com ele.\n\n"
                f"{ctx}"
            )
            web = False  # auditor audita, não pesquisa

        if progresso:
            print(f"[{i}/{TOTAL}] {titulo}{' [web]' if web else ''}...", flush=True)

        prompt = FASE_TMPL.format(
            ideia=ideia,
            contexto=ctx,
            n=i,
            total=TOTAL,
            titulo=titulo,
            instrucao=instrucao,
        )

        if web:
            try:
                resposta, urls = llm.research(
                    system_blocks(True),
                    prompt,
                    require_web=True,
                    rotulo=f"f{i}",
                    max_tokens=config.MAX_TOKENS_FASE,
                )
                novas = [u for u in urls if u not in fontes]
                fontes.extend(novas)

                datadas = evidencias.extrair(resposta)
                citadas.extend(datadas)
                if orfas := evidencias.urls_sem_data(resposta, urls):
                    registro.add(
                        fase=f"{i}. {titulo}",
                        descricao=(
                            f"{len(orfas)} fonte(s) citada(s) sem data de "
                            "publicação — recência não auditável"
                        ),
                        nivel=Nivel.MEDIA,
                        como_obter="marcar cada fonte como [URL | MM/AAAA]",
                    )
                if progresso:
                    print(
                        f"      {len(novas)} fontes novas, "
                        f"{len(datadas)} com data",
                        flush=True,
                    )
            except NoEvidenceError as e:
                registro.add(
                    fase=f"{i}. {titulo}",
                    descricao=f"nenhuma evidência externa obtida ({e})",
                    nivel=Nivel.ALTA,
                    como_obter="repetir a busca web ou validar os números à mão",
                )
                if progresso:
                    print("      ⚠ sem evidência — fase marcada", flush=True)
                # Degrada para o system SEM web: pedir evidência a quem não
                # pode buscar é o convite direto à confabulação.
                resposta, _ = llm.research(
                    system_blocks(False),
                    prompt,
                    require_web=False,
                    rotulo=f"f{i}",
                    max_tokens=config.MAX_TOKENS_FASE,
                )
                resposta = (
                    "> ⚠ **SEM EVIDÊNCIA EXTERNA** — nenhuma busca web foi "
                    "executada nesta fase. Trate todos os números abaixo como "
                    "estimativa não verificada.\n\n" + resposta
                )
        else:
            resposta = llm.complete(
                system_blocks(False),
                prompt,
                rotulo=f"f{i}",
                max_tokens=config.MAX_TOKENS_FASE,
            )

        blocos.append((titulo, resposta.strip()))

    if not any(t == AUDITORIA for t, _ in blocos):
        registro.add(
            fase="pipeline",
            descricao=(
                f"nenhuma fase {AUDITORIA!r} foi executada: o relatório não tem "
                "revisão adversarial para acatar"
            ),
            nivel=Nivel.BLOQUEANTE,
            como_obter=f"incluir {AUDITORIA!r} em prompts.FASES",
        )

    # Funil recalculado pelo sistema e recência das fontes: os dois viram
    # pendência ANTES de o score ser computado.
    _, funil_md = _montar_funil(blocos, registro, citadas, progresso)
    evidencias.auditar(citadas, registro)

    if progresso:
        print("[final] Relatório...", flush=True)

    # A rubrica vive no system cacheado; o prompt não a repete.
    contexto_final = _contexto(blocos)
    if funil_md:
        contexto_final += (
            "\n\n## Funil recalculado pelo sistema (autoritativo)\n"
            "As faixas abaixo substituem qualquer número de mercado divergente "
            f"nas fases acima.\n{funil_md}"
        )

    base = RELATORIO_TMPL.format(
        ideia=ideia,
        contexto=contexto_final,
        contrato=CONTRATO_AVALIACAO,
        ids=ids_str(RUBRICA),
    )

    bruto, notas, relatorio = "", None, ""
    for t in range(1, TENTATIVAS_CONTRATO + 1):
        p = base if t == 1 else base + (
            "\n\nATENÇÃO: sua resposta anterior violou o formato. A PRIMEIRA "
            "linha deve ser exatamente 'NOTAS: ' seguida de todos os "
            f"critérios ({ids_str(RUBRICA)}) no formato id=nota, "
            "separados por ponto e vírgula, com notas de 0 a 10. Nada antes dela."
        )
        bruto = llm.complete(
            system_blocks(True),
            p,
            rotulo=f"relatorio:{t}",
            max_tokens=config.MAX_TOKENS_RELATORIO,
        ).strip()
        try:
            notas, novas_pend, relatorio = _extrair_avaliacao(bruto)
            registro.estende(novas_pend)
            break
        except ValueError as e:
            if progresso:
                print(
                    f"      ⚠ contrato violado ({t}/{TENTATIVAS_CONTRATO}): {e}",
                    flush=True,
                )
    else:
        relatorio = bruto
        registro.add(
            fase="relatório final",
            descricao=(
                "o avaliador não emitiu notas por critério; não há score "
                "auditável para este relatório"
            ),
            nivel=Nivel.BLOQUEANTE,
            como_obter="reexecutar a validação",
        )

    doc = _montar_doc(
        ideia, blocos, relatorio, llm, fontes, citadas, registro, notas, funil_md
    )
    return doc, llm


# ────────────────────────────────────────────────────────────────────────────
def _montar_doc(
    ideia: str,
    blocos: list[tuple[str, str]],
    relatorio: str,
    llm: LLM,
    fontes: list[str],
    citadas: list[Fonte],
    registro: RegistroPendencias,
    notas: dict[str, float] | None,
    funil_md: str = "",
) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    fases = [b for b in blocos if b[0] != AUDITORIA]
    auditoria = next((c for t, c in blocos if t == AUDITORIA), "")

    tabela = ""
    if notas is None:
        cab_vered = (
            "**Veredicto:** ⚠ notas por critério não identificadas — "
            "sem score auditável, revise manualmente antes de decidir"
        )
        m = RE_FINAL.search(relatorio)
        if m and 0 <= int(m.group(1)) <= 100:
            cab_vered += (
                f"  \n_O texto menciona 'score final {m.group(1)}', "
                "não validado pela rubrica e sem valor decisório._"
            )
    else:
        bruto = RUBRICA.score(notas)
        final = registro.aplicar_em(bruto)
        violados = RUBRICA.eliminatorios_violados(notas)
        tabela = RUBRICA.tabela_markdown(notas)

        linhas = [
            f"**Score bruto (rubrica):** {bruto}/100  ",
            f"**Penalidade por pendências:** -{registro.penalidade}  ",
            f"**Score final:** {final}/100  ",
        ]
        if registro.tem_bloqueio:
            linhas.append("**Veredicto:** INSUFICIENTE PARA DECIDIR  ")
            linhas.append(
                "_Há pendências bloqueantes: premissas centrais não verificadas. "
                "O score é informativo e não autoriza investimento._"
            )
        elif violados:
            linhas.append("**Veredicto:** REPROVADO  ")
            linhas.append(
                "_Critério eliminatório violado: "
                + ", ".join(f"`{v}`" for v in violados)
                + ". Rebaixamento independe do score._"
            )
        else:
            linhas.append(f"**Veredicto:** {rotulo_para(final)}  ")
            linhas.append("_Derivado das faixas em rubrica.VEREDICTOS._")
        cab_vered = "\n".join(linhas)

    if registro.tem_bloqueio or registro.tem_ressalva:
        aviso = (
            "> ⚠ **RELATÓRIO PARCIAL.** Ocorrências que reduzem a "
            "confiabilidade:\n>\n"
            + "\n".join(
                f"> - {p}"
                for p in registro.bloqueantes + registro.por_nivel(Nivel.ALTA)
            )
        )
    elif citadas:
        recentes = sum(1 for f in citadas if f.usavel())
        aviso = (
            f"> ✅ Análise fundamentada em {len(fontes)} fontes web, "
            f"{recentes} de {len(citadas)} afirmações datadas dentro da janela "
            "de recência (ver auditoria de fontes)."
        )
    elif fontes:
        aviso = (
            f"> ⚠ {len(fontes)} fontes consultadas, nenhuma com data de "
            "publicação identificável. A recência dos números não foi auditada."
        )
    else:
        aviso = (
            "> ⚠ Análise sem fontes externas. Itens marcados como [ESTIMATIVA] "
            "ou [REQUER VERIFICAÇÃO] não são dados confirmados."
        )

    partes = [
        "# Validação de Infoproduto",
        f"**Ideia:** {ideia}",
        f"**Data:** {agora}  \n"
        f"**Modelo:** {llm.model}  \n"
        f"**Chamadas:** {llm.usage.calls}  \n"
        f"**Buscas web:** {llm.usage.web_searches}  \n"
        f"**Custo:** US$ {llm.usage.cost:.4f}",
        cab_vered,
        aviso,
        "---",
        "# Relatório Final",
        relatorio,
    ]

    if tabela:
        partes += ["---", f"# Pontuação por Critério\n\n{tabela}"]

    if funil_md:
        partes += ["---", funil_md]

    partes += ["---", f"# Pendências\n\n{registro.markdown()}"]

    if secao_fontes := evidencias.secao(citadas):
        partes += ["---", secao_fontes]

    partes += ["---", "# Análise Detalhada"]

    for i, (titulo, conteudo) in enumerate(fases, 1):
        partes.append(f"## Fase {i}/{len(fases)} — {titulo}\n\n{conteudo}")

    if auditoria:
        partes += ["---", f"# Auditoria Interna\n\n{auditoria}"]

    if fontes:
        lista = "\n".join(f"{i}. {u}" for i, u in enumerate(sorted(fontes), 1))
        partes += ["---", f"# Bibliografia\n\n{lista}"]

    partes += ["---", f"# Consumo\n\n```\n{llm.usage.breakdown()}\n```"]

    return "\n\n".join(partes) + "\n"
