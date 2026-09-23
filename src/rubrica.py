# src/rubrica.py
"""Fonte única de verdade da avaliação: critérios, pesos, faixas e parsing.

Nada além deste módulo decide nota, score ou veredicto. `config.py` não
duplica as faixas — a divergência silenciosa entre 80/60/40 e 75/55 já
custou um relatório errado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── Critérios ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Criterio:
    id: str
    fase: str
    titulo: str
    peso: float
    pergunta: str
    ancora_10: str
    ancora_5: str
    ancora_0: str


CRITERIOS: tuple[Criterio, ...] = (
    Criterio(
        id="clareza",
        fase="1",
        titulo="Clareza do produto",
        peso=0.10,
        pergunta="O problema, a transformação e o público cabem em uma frase?",
        ancora_10="Uma frase nomeia dor, público e resultado mensurável.",
        ancora_5="Promessa compreensível, mas genérica ou sem público definido.",
        ancora_0="Descrição vaga; não se sabe quem compra nem o que muda.",
    ),
    Criterio(
        id="mercado",
        fase="2",
        titulo="Tamanho e direção do mercado",
        peso=0.15,
        pergunta="TAM/SAM/SOM sustentam o faturamento pretendido? Cresce?",
        ancora_10="SOM com fonte citada, folga sobre a meta, tendência de alta.",
        ancora_5="Ordem de grandeza plausível, sem fonte; setor estável.",
        ancora_0="Mercado nichado demais para a meta, ou em declínio claro.",
    ),
    Criterio(
        id="concorrencia",
        fase="3",
        titulo="Concorrência e diferenciação",
        peso=0.15,
        pergunta="Há concorrentes vendendo? A oferta ocupa uma lacuna real?",
        ancora_10="Concorrentes com prova de venda e uma lacuna nomeável explorada.",
        ancora_5="Concorrentes existem; diferenciação depende de execução.",
        ancora_0="Zero concorrentes (mercado inexistente) ou paridade total.",
    ),
    Criterio(
        id="demanda",
        fase="4",
        titulo="Demanda comprovada",
        peso=0.25,
        pergunta="O público busca isso, reclama disso e já paga por isso?",
        ancora_10="Busca com volume, dor articulada em comunidades, ticket conhecido.",
        ancora_5="Interesse visível, sem evidência de pagamento.",
        ancora_0="Nenhum sinal de busca ou de dor; hipótese do fundador.",
    ),
    Criterio(
        id="viabilidade",
        fase="5",
        titulo="Viabilidade econômica",
        peso=0.20,
        pergunta="Preço, custo e conversão fecham acima do ponto de equilíbrio?",
        ancora_10="Break-even atingível com conversão conservadora; margem escalável.",
        ancora_5="Fecha só com conversão otimista ou CAC ainda desconhecido.",
        ancora_0="Custo de aquisição maior que o ticket; modelo não fecha.",
    ),
    Criterio(
        id="prova_social",
        fase="6",
        titulo="Prova social disponível",
        peso=0.10,
        pergunta="Existe audiência, autoridade ou comunidade acessível hoje?",
        ancora_10="Lista, engajamento ou parceiros já dispostos a endossar.",
        ancora_5="Audiência pequena ou emprestada; nada testado.",
        ancora_0="Sem audiência, sem autoridade, sem acesso ao nicho.",
    ),
    Criterio(
        id="risco",
        fase="7",
        titulo="Risco e testabilidade",
        peso=0.05,
        pergunta="É possível invalidar a ideia rápido e barato?",
        ancora_10="Teste definido, abaixo de R$ 500 e uma semana, com métrica de corte.",
        ancora_5="Teste possível, mas exige produto parcial.",
        ancora_0="Só se valida construindo tudo; riscos sem mitigação.",
    ),
)

# Nota mínima aceitável. Abaixo disso o veredicto cai para REPROVADO,
# qualquer que seja o score: não se aprova oferta sem demanda porque as
# outras notas compensaram na média.
CRITERIOS_ELIMINATORIOS: dict[str, float] = {
    "demanda": 4.0,
    "viabilidade": 4.0,
}

VEREDICTOS: tuple[tuple[float, str], ...] = (
    (75, "APROVADO"),
    (55, "APROVADO COM RESSALVAS"),
    (40, "REPROVADO — REPOSICIONAR"),
    (0, "REPROVADO"),
)

PISO = VEREDICTOS[-1][1]


def rotulo_para(score: float) -> str:
    """Traduz score 0–100 em veredicto. Única tradutora do projeto."""
    if not 0 <= score <= 100:
        raise ValueError(f"score fora do intervalo 0–100: {score!r}")
    for corte, nome in VEREDICTOS:
        if score >= corte:
            return nome
    return PISO


# ── Rubrica ──────────────────────────────────────────────────────────────


class Rubrica:
    """Cálculo de score e veredicto sobre o conjunto fixo de critérios."""

    def __init__(self, criterios: tuple[Criterio, ...] = CRITERIOS) -> None:
        soma = round(sum(c.peso for c in criterios), 6)
        if soma != 1.0:
            raise ValueError(f"pesos somam {soma}, deveriam somar 1.0")
        if len({c.id for c in criterios}) != len(criterios):
            raise ValueError("ids de critério duplicados")
        self.criterios = criterios
        self._por_id = {c.id: c for c in criterios}

    def ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.criterios)

    def por_id(self, cid: str) -> Criterio:
        return self._por_id[cid]

    # ── Validação ────────────────────────────────────────────────────────
    def _valida(self, notas: dict[str, float]) -> None:
        esperados = set(self.ids())
        recebidos = set(notas)
        if faltando := esperados - recebidos:
            raise ValueError(f"notas ausentes: {sorted(faltando)}")
        if sobrando := recebidos - esperados:
            # Um typo zeraria o peso do critério real sem nenhum aviso.
            raise ValueError(f"critérios desconhecidos: {sorted(sobrando)}")
        for cid, n in notas.items():
            if not isinstance(n, (int, float)) or isinstance(n, bool):
                raise ValueError(f"nota de {cid} não é número: {n!r}")
            if not 0 <= n <= 10:
                raise ValueError(f"nota de {cid} fora do intervalo 0–10: {n!r}")

    # ── Cálculo ──────────────────────────────────────────────────────────
    def score(self, notas: dict[str, float]) -> float:
        self._valida(notas)
        bruto = sum(notas[c.id] * c.peso for c in self.criterios) * 10
        return round(bruto, 2)

    def eliminatorios_violados(self, notas: dict[str, float]) -> list[str]:
        self._valida(notas)
        return [
            cid
            for cid, minimo in CRITERIOS_ELIMINATORIOS.items()
            if notas[cid] < minimo
        ]

    def veredicto(
        self,
        notas: dict[str, float],
        score_final: float | None = None,
    ) -> tuple[str, float, list[str]]:
        """Devolve (rótulo, score, eliminatórios violados).

        `score_final` permite injetar o score já penalizado por pendências;
        omitido, usa o score bruto das notas.
        """
        bruto = self.score(notas)
        efetivo = bruto if score_final is None else round(float(score_final), 2)
        violados = self.eliminatorios_violados(notas)
        rotulo = PISO if violados else rotulo_para(efetivo)
        return rotulo, efetivo, violados

    # ── Renderização ─────────────────────────────────────────────────────
    def tabela_markdown(self, notas: dict[str, float] | None = None) -> str:
        linhas = [
            "| Critério | Peso | Nota | Contribuição |",
            "|---|---:|---:|---:|",
        ]
        for c in self.criterios:
            if notas is None:
                nota = contrib = "—"
            else:
                n = notas[c.id]
                nota = f"{n:g}"
                contrib = f"{n * c.peso * 10:.1f}"
            linhas.append(
                f"| {c.titulo} (`{c.id}`) | {c.peso:.0%} | {nota} | {contrib} |"
            )
        if notas is None:
            return "\n".join(linhas)

        s = self.score(notas)
        linhas.append(f"| **Score** | 100% | | **{s:.1f}** |")
        if violados := self.eliminatorios_violados(notas):
            nomes = ", ".join(f"`{v}`" for v in violados)
            linhas.append("")
            linhas.append(
                f"> ⚠️ **Eliminatórios violados:** {nomes} — "
                f"veredicto rebaixado a {PISO} independentemente do score."
            )
        return "\n".join(linhas)


def ancoras_markdown(rubrica: Rubrica | None = None) -> str:
    """Âncoras de pontuação para colar no prompt. Conteúdo estático."""
    r = rubrica or Rubrica()
    blocos: list[str] = []
    for c in r.criterios:
        elim = CRITERIOS_ELIMINATORIOS.get(c.id)
        aviso = (
            f" **Eliminatório: nota < {elim:g} reprova o projeto.**" if elim else ""
        )
        blocos.append(
            f"### Fase {c.fase} — {c.titulo} (`{c.id}`, peso {c.peso:.0%})\n"
            f"{c.pergunta}{aviso}\n"
            f"- **10** — {c.ancora_10}\n"
            f"- **5** — {c.ancora_5}\n"
            f"- **0** — {c.ancora_0}"
        )
    return "\n\n".join(blocos)


# ── Contrato de saída e parsing ──────────────────────────────────────────

_IDS = "; ".join(f"{c.id}=<0-10>" for c in CRITERIOS)

CONTRATO_NOTAS = (
    "A primeira linha da resposta deve ser exatamente, sem markdown:\n"
    f"NOTAS: {_IDS}\n"
    "Use ponto ou vírgula decimal, um único número por critério, todos os "
    "sete presentes. Não escreva nada antes dessa linha."
)

_RE_NOTAS = re.compile(r"^\s*NOTAS\s*:(?P<corpo>[^\n]*)", re.IGNORECASE)
_RE_PAR = re.compile(r"(?P<id>[a-z_]+)\s*=\s*(?P<valor>\d+(?:[.,]\d+)?)", re.I)


def parse_notas(texto: str) -> tuple[dict[str, float], str]:
    """Lê a linha `NOTAS:` e devolve (notas, resto do texto).

    Levanta ValueError em vez de adivinhar: nota inventada contamina o
    veredicto inteiro.
    """
    m = _RE_NOTAS.match(texto)
    if not m:
        raise ValueError(
            "resposta não começa com a linha NOTAS: exigida pelo contrato"
        )
    pares = _RE_PAR.findall(m.group("corpo"))
    if not pares:
        raise ValueError("linha NOTAS: sem pares id=valor")

    notas: dict[str, float] = {}
    for cid, valor in pares:
        notas[cid.lower()] = float(valor.replace(",", "."))

    esperados = {c.id for c in CRITERIOS}
    if faltando := esperados - set(notas):
        raise ValueError(f"notas ausentes na linha NOTAS: {sorted(faltando)}")
    if sobrando := set(notas) - esperados:
        raise ValueError(f"critérios desconhecidos: {sorted(sobrando)}")

    resto = texto[m.end():].lstrip("\n")
    return notas, resto


# ── Prefixo estático para cache de prompt ────────────────────────────────
# Montado uma vez na importação. É este bloco que recebe `cache_control`
# nas chamadas: passa dos 1.024 tokens mínimos e não varia entre fases,
# então a leitura cai de US$ 3,00 para US$ 0,30 por milhão.

_R = Rubrica()

PREFIXO_ESTATICO = f"""## Rubrica de avaliação

Atribua nota 0–10 a cada critério, ancorada nas descrições abaixo. Nota
sem evidência citada é opinião: nesse caso registre pendência e puxe a
nota para baixo.

{ancoras_markdown(_R)}

## Faixas de veredicto

| Score | Veredicto | Significado |
|---:|---|---|
| ≥ 75 | APROVADO | Seguir para pré-venda. |
| 55–74 | APROVADO COM RESSALVAS | Seguir só após resolver as pendências listadas. |
| 40–54 | REPROVADO — REPOSICIONAR | Dor existe, oferta está errada: mudar público, formato ou preço. |
| < 40 | REPROVADO | Não construir. |

Violar qualquer critério eliminatório rebaixa o veredicto a REPROVADO,
por mais alto que seja o score.

## Contrato de saída

{CONTRATO_NOTAS}
"""

__all__ = [
    "CONTRATO_NOTAS",
    "CRITERIOS",
    "CRITERIOS_ELIMINATORIOS",
    "PISO",
    "PREFIXO_ESTATICO",
    "VEREDICTOS",
    "Criterio",
    "Rubrica",
    "ancoras_markdown",
    "parse_notas",
    "rotulo_para",
]
