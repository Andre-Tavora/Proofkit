<h1 align="center">🔍 ProofKit</h1>
<p align="center"><strong>Validador de Infoprodutos orientado a evidências</strong></p>

<strong>🚧 Projeto em construção — previsão de publicação: 48h 🚧</strong>

</p>

<p align="center">
  Pipeline de <em>AI Agents</em> que valida ideias de produtos digitais com dados reais de mercado
  <strong>antes</strong> do investimento em produção.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20GPT-8A2BE2" alt="LLM">
  <img src="https://img.shields.io/badge/RAG-Web%20Search-FF6F00" alt="RAG">
  <img src="https://img.shields.io/badge/status-em%20construção-yellow" alt="Status">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

<p align="center">
  <img src="docs/assets/banner.png" alt="Demonstração do Validador de Infoprodutos" width="100%">
</p>

---

## 📌 Sobre o Projeto

**Validador de Infoprodutos** é um sistema de **orquestração de LLMs** que substitui o "achismo" na
validação de produtos digitais por um processo auditável e baseado em evidências.

O usuário submete uma ideia — curso, e-book, mentoria, comunidade, assinatura ou SaaS — e o pipeline
executa **7 fases sequenciais de pesquisa**, cruzando busca web em tempo real com análise crítica,
até emitir um **veredito** (Aprovado / Aprovado com ressalvas / Reprovado) e um **score de 0 a 100**.

> **Diferencial técnico:** cada afirmação numérica é rastreável até a fonte, e o score final é
> **descontado pela qualidade da evidência**. Análise com 15% de fontes datadas não vale o mesmo
> que uma com 80%.

---

## ⚙️ As 7 Fases da Metodologia

|  #  | Fase                        | Entregável                                                           |
| :-: | --------------------------- | -------------------------------------------------------------------- |
|  1  | **Clareza do Produto**      | Problema central, transformação, nicho primário/secundário           |
|  2  | **Análise de Mercado**      | TAM, SAM, SOM + curva de tendência                                   |
|  3  | **Análise de Concorrência** | Mapa competitivo, gaps, Proposta Única de Valor                      |
|  4  | **Validação de Demanda**    | Palavras-chave reais, intensidade da dor, ticket médio               |
|  5  | **Viabilidade de Negócio**  | Estrutura de custos, break-even, pricing, escalabilidade             |
|  6  | **Prova Social**            | Sinais de engajamento, influenciadores, estratégia de pré-lançamento |
|  7  | **Riscos & Mitigação**      | Top 3 riscos + **MVP de menor custo** para testar a hipótese         |

---

## 🧠 Arquitetura

```
src/
├─ evidencia.py     # Scoring de confiança: inferência de data, peso temporal, gates
├─ web.py           # Camada de busca (duas passadas: recorte temporal + fallback amplo)
├─ fases/           # Uma fase = query + template + threshold mínimo de fontes datadas
├─ pipeline.py      # Orquestração, budget guard, degradação controlada
└─ relatorio.py     # Score ajustado por confiança + veredicto final
```

**Decisões de engenharia:**

- 🎯 **Peso temporal da evidência** — fontes sem data recebem confiança `0.35`; fontes datadas
  decaem `0.25` por ano de idade.
- 🔁 **Busca em duas passadas** — recorte temporal primeiro, fallback amplo se o recall cair,
  preservando cobertura sem sacrificar recência.
- 🛡️ **Degradação controlada** — ao estourar o orçamento de chamadas, o pipeline reduz escopo
  e sinaliza, em vez de abortar.
- 🧪 **Núcleo puro e testável** — `evidencia.py` não faz I/O, permitindo cobertura por `pytest`.

---

## 🚀 Stack & Competências

`Python` · `LLM Orchestration` · `Prompt Engineering` · `RAG (Retrieval-Augmented Generation)`
`AI Agents` · `Multi-Agent Systems` · `Web Search API` · `REST API Integration` · `FastAPI`
`Data-Driven Decision Making` · `Market Research` · `TAM/SAM/SOM` · `Product Discovery`
`Growth Marketing` · `CRO` · `Unit Testing (Pytest)` · `Clean Architecture` · `Docker` · `Git/CI-CD`

---

## 🏁 Como Executar

```bash
git clone https://github.com/<seu-usuario>/validador-infoprodutos.git
cd validador-infoprodutos

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env    # preencha as chaves de API
python -m src.main --ideia "Mentoria de tráfego pago para dentistas"
```

---

## 🗺️ Roadmap

- [x] Núcleo das 7 fases
- [x] Camada de scoring de evidência
- [ ] Dashboard web do relatório _(em construção)_
- [ ] Exportação em PDF
- [ ] Cache persistente de buscas

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja [`LICENSE`](LICENSE).

<p align="center">
  Desenvolvido por <strong>Carlos</strong> · Fortaleza, CE 🇧🇷<br>
  <a href="https://www.linkedin.com/in/andreorganizacional/">LinkedIn</a> ·
  <a href="mailto:andre.tavora3@gmail.com">E-mail</a>
</p>
