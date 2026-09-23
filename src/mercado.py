"""Funil TAM/SAM/SOM com teto de 3 fatores e faixa obrigatória (nunca ponto único)."""

from dataclasses import dataclass, field

MAX_FATORES = 3
BANDA_PADRAO = 0.30  # ±30% quando o fator é estimado sem faixa própria


class ExcessoDeFatores(ValueError):
    pass


@dataclass
class Fator:
    nome: str
    base: float
    verificado: bool = False
    piso: float | None = None
    teto: float | None = None
    fonte: str = ""

    def __post_init__(self):
        if not 0 < self.base <= 1:
            raise ValueError(f"{self.nome}: fator deve estar em (0, 1]")
        if self.verificado:
            self.piso = self.piso if self.piso is not None else self.base
            self.teto = self.teto if self.teto is not None else self.base
        else:
            if self.piso is None:
                self.piso = self.base * (1 - BANDA_PADRAO)
            if self.teto is None:
                self.teto = min(1.0, self.base * (1 + BANDA_PADRAO))
        if not self.piso <= self.base <= self.teto:
            raise ValueError(f"{self.nome}: piso <= base <= teto violado")

    @property
    def rotulo(self) -> str:
        return "VERIFICADO" if self.verificado else "ESTIMATIVA"


@dataclass
class Faixa:
    pessimista: float
    base: float
    otimista: float

    @property
    def amplitude(self) -> float:
        return self.otimista / self.pessimista if self.pessimista else float("inf")

    @property
    def confiavel(self) -> bool:
        return self.amplitude <= 3.0

    def fmt(self, moeda=False, casas=0) -> str:
        def n(v):
            s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {s}" if moeda else s
        return f"{n(self.pessimista)} – **{n(self.base)}** – {n(self.otimista)}"


@dataclass
class Etapa:
    nome: str
    fatores: list = field(default_factory=list)

    def __post_init__(self):
        if len(self.fatores) > MAX_FATORES:
            raise ExcessoDeFatores(
                f"{self.nome}: {len(self.fatores)} fatores. "
                f"Máximo é {MAX_FATORES} — agregue ou verifique antes de prosseguir."
            )

    @property
    def estimados(self) -> int:
        return sum(1 for f in self.fatores if not f.verificado)

    def aplicar(self, entrada: Faixa) -> Faixa:
        p = b = o = 1.0
        for f in self.fatores:
            p *= f.piso
            b *= f.base
            o *= f.teto
        return Faixa(entrada.pessimista * p, entrada.base * b, entrada.otimista * o)


@dataclass
class Funil:
    universo: float
    universo_fonte: str
    ticket: float
    etapas: list = field(default_factory=list)

    def resultados(self) -> list:
        atual = Faixa(self.universo, self.universo, self.universo)
        saida = [("Universo", atual, None)]
        for e in self.etapas:
            atual = e.aplicar(atual)
            saida.append((e.nome, atual, e))
        return saida

    @property
    def final(self) -> Faixa:
        return self.resultados()[-1][1]

    def receita(self, faixa: Faixa) -> Faixa:
        return Faixa(
            faixa.pessimista * self.ticket,
            faixa.base * self.ticket,
            faixa.otimista * self.ticket,
        )

    def markdown(self) -> str:
        res = self.resultados()
        out = [
            "## FUNIL DE MERCADO",
            "",
            f"**Universo:** {self.universo:,.0f} — {self.universo_fonte}".replace(",", "."),
            "",
            "| Etapa | Pessimista – Base – Otimista | Receita anual (base) | Fatores estimados |",
            "|---|---|---|---:|",
        ]
        for nome, faixa, etapa in res:
            rec = self.receita(faixa)
            est = "—" if etapa is None else f"{etapa.estimados}/{len(etapa.fatores)}"
            out.append(f"| {nome} | {faixa.fmt()} | {rec.fmt(moeda=True)} | {est} |")

        out += ["", "### Fatores aplicados", ""]
        for e in self.etapas:
            out.append(f"**{e.nome}**")
            for f in e.fatores:
                banda = f"{f.piso:.0%}–{f.teto:.0%}"
                fonte = f" — {f.fonte}" if f.fonte else ""
                out.append(f"- {f.nome}: {f.base:.0%} (faixa {banda}) `[{f.rotulo}]`{fonte}")
            out.append("")

        fim = self.final
        out += [
            "### Leitura obrigatória",
            "",
            f"Amplitude pessimista→otimista: **{fim.amplitude:.1f}x**.",
            "",
        ]
        if not fim.confiavel:
            out.append(
                "> A amplitude excede 3x. Este funil **não sustenta decisão de investimento** "
                "nem cálculo de break-even. Verifique fatores antes de usar."
            )
        else:
            out.append(
                "> Use sempre o cenário **pessimista** para testar break-even. "
                "O valor base não é previsão, é ponto médio de faixa."
            )
        return "\n".join(out).rstrip() + "\n"


def checar_breakeven(alunos_necessarios: int, faixa: Faixa) -> str:
    if alunos_necessarios <= faixa.pessimista:
        return (
            f"✅ Break-even de {alunos_necessarios} alunos está **abaixo do cenário pessimista** "
            f"({faixa.pessimista:,.0f}).".replace(",", ".")
        )
    if alunos_necessarios <= faixa.base:
        return (
            f"⚠️ Break-even de {alunos_necessarios} alunos exige desempenho **acima do pessimista** "
            f"({faixa.pessimista:,.0f}) e abaixo do base ({faixa.base:,.0f}).".replace(",", ".")
        )
    if alunos_necessarios <= faixa.otimista:
        return (
            f"🚨 Break-even de {alunos_necessarios} alunos só ocorre **perto do cenário otimista** "
            f"({faixa.otimista:,.0f}). Risco alto."
        )
    return (
        f"❌ Break-even de {alunos_necessarios} alunos está **acima do cenário otimista** "
        f"({faixa.otimista:,.0f}). Modelo inviável no preço atual."
    )
