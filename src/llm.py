# src/llm.py
from __future__ import annotations

import inspect
import time
from collections import defaultdict
from dataclasses import dataclass, field

from . import config

System = str | list[dict]


class LLMError(RuntimeError):
    """Falha de comunicação, contrato ou configuração."""


class NoEvidenceError(LLMError):
    """A fase exigia busca web e o modelo não citou nenhuma fonte."""


# ─────────────────────────────────────────────────────────────────────
@dataclass
class Bucket:
    """Tokens de um único modelo. Somar Haiku com Sonnet num só total
    faz a triagem barata parecer cara e apaga a economia do relatório."""

    tokens_in: int = 0
    tokens_out: int = 0
    cache_write: int = 0
    cache_read: int = 0

    def custo(self, modelo: str) -> float:
        p = config.precos(modelo)
        m = 1_000_000
        return (
            self.tokens_in / m * p["in"]
            + self.tokens_out / m * p["out"]
            + self.cache_write / m * p["cw"]
            + self.cache_read / m * p["cr"]
        )


@dataclass
class Usage:
    calls: int = 0
    web_searches: int = 0
    retries: int = 0
    por_modelo: dict[str, Bucket] = field(
        default_factory=lambda: defaultdict(Bucket)
    )
    _log: list[tuple[str, str, int, int, int, int]] = field(default_factory=list)

    def add(self, rotulo: str, u, modelo: str) -> None:
        """Acumula o bloco `usage` de uma resposta da API."""
        ti = getattr(u, "input_tokens", 0) or 0
        to = getattr(u, "output_tokens", 0) or 0
        cw = getattr(u, "cache_creation_input_tokens", 0) or 0
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        srv = getattr(u, "server_tool_use", None)
        ws = getattr(srv, "web_search_requests", 0) or 0

        b = self.por_modelo[modelo]
        b.tokens_in += ti
        b.tokens_out += to
        b.cache_write += cw
        b.cache_read += cr

        self.calls += 1
        self.web_searches += ws
        self._log.append((rotulo, modelo, ti, to, cr, ws))

    # ── Agregados ────────────────────────────────────────────────────
    @property
    def tokens_in(self) -> int:
        return sum(b.tokens_in for b in self.por_modelo.values())

    @property
    def tokens_out(self) -> int:
        return sum(b.tokens_out for b in self.por_modelo.values())

    @property
    def cache_write(self) -> int:
        return sum(b.cache_write for b in self.por_modelo.values())

    @property
    def cache_read(self) -> int:
        return sum(b.cache_read for b in self.por_modelo.values())

    @property
    def cost(self) -> float:
        return sum(
            b.custo(modelo) + 0.0 for modelo, b in self.por_modelo.items()
        ) + self.web_searches * config.PRICE_SEARCH

    @property
    def economia_cache(self) -> float:
        """Quanto o cache poupou: o que os tokens lidos teriam custado
        como input cheio, menos o que custaram de fato."""
        total = 0.0
        for modelo, b in self.por_modelo.items():
            p = config.precos(modelo)
            total += b.cache_read / 1_000_000 * (p["in"] - p["cr"])
        return total

    def breakdown(self) -> str:
        cab = f"{'chamada':<22} {'modelo':<10} {'in':>8} {'out':>8} {'cache↓':>8} {'web':>4}"
        linhas = [cab, "-" * len(cab)]
        for rotulo, modelo, ti, to, cr, ws in self._log:
            fam = modelo.split("-")[1] if "-" in modelo else modelo
            linhas.append(
                f"{rotulo[:22]:<22} {fam[:10]:<10} {ti:>8,} {to:>8,} "
                f"{cr:>8,} {ws:>4}"
            )
        linhas += [
            "-" * len(cab),
            f"{'TOTAL':<22} {'':<10} {self.tokens_in:>8,} "
            f"{self.tokens_out:>8,} {self.cache_read:>8,} {self.web_searches:>4}",
            "",
        ]
        for modelo, b in sorted(self.por_modelo.items()):
            linhas.append(f"{modelo:<34} US$ {b.custo(modelo):.4f}")
        linhas += [
            f"{'buscas web':<34} US$ {self.web_searches * config.PRICE_SEARCH:.4f}",
            "",
            f"cache write  : {self.cache_write:,} tokens",
            f"cache read   : {self.cache_read:,} tokens",
            f"cache poupou : US$ {self.economia_cache:.4f}",
            f"retentativas : {self.retries}",
            f"CUSTO TOTAL  : US$ {self.cost:.4f}",
        ]
        return "\n".join(linhas)


# ─────────────────────────────────────────────────────────────────────
def _normaliza_system(system: System) -> list[dict]:
    """Aceita string ou blocos já montados. Blocos preservam `cache_control`;
    envolver tudo num único dict apagaria a marcação e o cache nunca acertaria."""
    if isinstance(system, str):
        return [{"type": "text", "text": system}]
    if isinstance(system, list):
        if not system:
            raise LLMError("system vazio")
        for b in system:
            if not isinstance(b, dict) or "text" not in b:
                raise LLMError(f"bloco de system inválido: {b!r}")
        return system
    raise LLMError(f"system deve ser str ou list[dict], recebi {type(system).__name__}")


class LLM:
    """Wrapper fino sobre a API Anthropic, com contabilidade de custo.

    Regra central: `require_web=False` NÃO anexa a ferramenta de busca.
    Prometer no system prompt que não há web enquanto a tool existe é o
    caminho mais curto para o modelo buscar e não citar.
    """

    def __init__(self, model: str | None = None) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as e:  # noqa: BLE001
            raise LLMError("pacote ausente: pip install anthropic") from e

        self.model = model or config.MODEL_MAIN
        self.usage = Usage()
        self._client = Anthropic(api_key=config.api_key(), timeout=config.TIMEOUT)
        self._aceitos = self._parametros_aceitos()

    # ── infraestrutura ───────────────────────────────────────────────
    def _parametros_aceitos(self) -> set[str] | None:
        """`None` quando o SDK aceita **kwargs livres."""
        params = inspect.signature(self._client.messages.create).parameters
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
            return None
        return set(params)

    def _sanitiza(self, kw: dict) -> dict:
        """Descarta parâmetros que a versão instalada do SDK não conhece
        (ex.: `temperature` em SDKs recentes)."""
        if self._aceitos is None:
            return kw
        return {k: v for k, v in kw.items() if k in self._aceitos}

    def _call(self, rotulo: str, modelo: str | None = None, **kw):
        from anthropic import APIStatusError, APITimeoutError, RateLimitError

        alvo = modelo or self.model
        kw = self._sanitiza(kw)
        ultima: Exception | None = None
        for t in range(1, config.TENTATIVAS + 1):
            try:
                r = self._client.messages.create(model=alvo, **kw)
                # Usa o modelo devolvido pela API, não o pedido: se houver
                # redirecionamento de alias, o preço acompanha.
                self.usage.add(rotulo, r.usage, getattr(r, "model", alvo))
                return r
            except (RateLimitError, APITimeoutError) as e:
                ultima = e
            except APIStatusError as e:
                if e.status_code < 500:  # 4xx não melhora ao repetir
                    raise LLMError(f"{rotulo}: HTTP {e.status_code} — {e}") from e
                ultima = e

            if t < config.TENTATIVAS:
                self.usage.retries += 1
                time.sleep(config.BACKOFF_BASE ** t)

        raise LLMError(
            f"{rotulo}: falhou em {config.TENTATIVAS} tentativas — {ultima}"
        )

    @staticmethod
    def _texto(resp) -> str:
        return "\n".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        ).strip()

    @staticmethod
    def _fontes(resp) -> list[str]:
        """URLs de citação e de resultado de busca, sem duplicatas, em ordem."""
        urls: list[str] = []

        def push(u) -> None:
            if isinstance(u, str) and u.startswith("http") and u not in urls:
                urls.append(u)

        for b in resp.content:
            tipo = getattr(b, "type", "")
            if tipo == "text":
                for c in getattr(b, "citations", None) or []:
                    push(getattr(c, "url", None))
            elif tipo == "web_search_tool_result":
                conteudo = getattr(b, "content", None) or []
                if isinstance(conteudo, list):
                    for item in conteudo:
                        push(getattr(item, "url", None))
        return urls

    # ── API pública ──────────────────────────────────────────────────
    def complete(
        self,
        system: System,
        prompt: str,
        rotulo: str = "complete",
        modelo: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Geração sem ferramentas."""
        r = self._call(
            rotulo,
            modelo=modelo,
            max_tokens=max_tokens or config.MAX_TOKENS,
            system=_normaliza_system(system),
            messages=[{"role": "user", "content": prompt}],
        )
        texto = self._texto(r)
        if not texto:
            raise LLMError(f"{rotulo}: resposta vazia (stop={r.stop_reason})")
        return texto

    def research(
        self,
        system: System,
        prompt: str,
        require_web: bool = True,
        rotulo: str = "research",
        modelo: str | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, list[str]]:
        """Com `require_web=True`, anexa a tool de busca e exige fontes.
        Com `False`, é um `complete` puro — sem tools, sem exigência."""
        if not require_web:
            texto = self.complete(
                system,
                prompt,
                rotulo=f"{rotulo}:noweb",
                modelo=modelo,
                max_tokens=max_tokens,
            )
            return texto, []

        r = self._call(
            f"{rotulo}:web",
            modelo=modelo,
            max_tokens=max_tokens or config.MAX_TOKENS,
            system=_normaliza_system(system),
            messages=[{"role": "user", "content": prompt}],
            tools=[{**config.WEB_TOOL, "user_location": config.USER_LOCATION}],
        )

        texto = self._texto(r)
        fontes = self._fontes(r)
        buscas = getattr(
            getattr(r.usage, "server_tool_use", None), "web_search_requests", 0
        ) or 0

        if not fontes:
            raise NoEvidenceError(
                f"{buscas} busca(s) executada(s), nenhuma fonte citada"
                if buscas
                else "o modelo não executou nenhuma busca"
            )
        if not texto:
            raise LLMError(f"{rotulo}: buscou mas não produziu texto")
        return texto, fontes
