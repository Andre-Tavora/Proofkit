<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>ProofKit — Validador de Infoprodutos</title>
<style>
  :root {
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --heading: #f0f6fc;
    --accent: #58a6ff;
    --accent2: #8a2be2;
    --green: #3fb950;
    --yellow: #d29922;
    --muted: #8b949e;
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 40px 20px;
  }
  .container {
    max-width: 880px;
    margin: 0 auto;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 48px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }
  h1 {
    text-align: center;
    font-size: 2.4em;
    color: var(--heading);
    margin-bottom: 4px;
  }
  .subtitle {
    text-align: center;
    color: var(--muted);
    font-size: 1.1em;
    margin-bottom: 8px;
  }
  .lead {
    text-align: center;
    max-width: 620px;
    margin: 16px auto 24px;
    color: var(--text);
  }
  .badges {
    text-align: center;
    margin-bottom: 32px;
  }
  .badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75em;
    font-weight: 600;
    margin: 2px 3px;
    color: #fff;
  }
  .badge.python { background: #3776AB; }
  .badge.llm { background: #8A2BE2; }
  .badge.rag { background: #FF6F00; }
  .badge.status { background: #3fb950; }
  .badge.license { background: #2ea043; }

hr {
border: none;
border-top: 1px solid var(--border);
margin: 36px 0;
}
h2 {
color: var(--heading);
font-size: 1.5em;
border-bottom: 1px solid var(--border);
padding-bottom: 8px;
margin-top: 40px;
}
h3 {
color: var(--heading);
font-size: 1.15em;
margin-top: 28px;
}
blockquote {
border-left: 4px solid var(--accent);
background: rgba(88,166,255,0.08);
margin: 16px 0;
padding: 12px 18px;
color: var(--text);
border-radius: 0 6px 6px 0;
}
ul, ol {
padding-left: 22px;
}
li { margin-bottom: 8px; }
code {
background: #1c2128;
color: #79c0ff;
padding: 2px 6px;
border-radius: 4px;
font-family: "SF Mono", Consolas, monospace;
font-size: 0.9em;
}
pre {
background: #010409;
border: 1px solid var(--border);
border-radius: 8px;
padding: 16px;
overflow-x: auto;
font-size: 0.88em;
}
pre code {
background: none;
color: #c9d1d9;
padding: 0;
}
table {
width: 100%;
border-collapse: collapse;
margin: 16px 0;
font-size: 0.92em;
}
th, td {
border: 1px solid var(--border);
padding: 8px 12px;
text-align: left;
}
th {
background: #1c2128;
color: var(--heading);
}
tr:nth-child(even) { background: rgba(255,255,255,0.02); }
.stack-tags {
text-align: left;
line-height: 2;
}
.stack-tags code {
margin-right: 4px;
}
.roadmap li {
list-style: none;
padding-left: 4px;
}
.roadmap li::before {
content: "☐ ";
color: var(--muted);
}
.roadmap li.done::before {
content: "☑ ";
color: var(--green);
}
footer {
text-align: center;
margin-top: 48px;
color: var(--muted);
font-size: 0.9em;
}
footer a {
color: var(--accent);
text-decoration: none;
}
footer a:hover { text-decoration: underline; }
.architecture-tree {
font-family: "SF Mono", Consolas, monospace;
font-size: 0.85em;
white-space: pre;
color: #a5d6ff;
}
.comment { color: #8b949e; }
</style>

</head>
<body>
<div class="container">

  <h1>🔍 ProofKit</h1>
  <p class="subtitle"><strong>Validador de Infoprodutos orientado a evidências</strong></p>

  <p class="lead">
    Pipeline de <em>AI Agents</em> que valida ideias de produtos digitais com dados reais de mercado
    <strong>antes</strong> do investimento em produção.
  </p>

  <div class="badges">
    <span class="badge python">Python 3.11+</span>
    <span class="badge llm">LLM: Claude</span>
    <span class="badge rag">RAG: Web Search</span>
    <span class="badge status">status: ativo</span>
    <span class="badge license">license: MIT</span>
  </div>

  <hr>

  <h2>📌 Sobre o Projeto</h2>
  <p>
    <strong>ProofKit</strong> é um sistema de <strong>orquestração de LLMs</strong> que substitui o
    "achismo" na validação de produtos digitais por um processo auditável e baseado em evidências.
  </p>
  <p>
    O usuário submete uma ideia — curso, e-book, mentoria, comunidade, assinatura ou SaaS. O pipeline
    aplica primeiro uma <strong>triagem barata</strong> e, se a ideia passar, executa as
    <strong>fases sequenciais de pesquisa</strong>, cruzando busca web em tempo real com análise
    crítica, até emitir um <strong>veredicto</strong> e um <strong>score de 0 a 100</strong>.
  </p>

  <blockquote>
    <strong>Diferencial técnico:</strong> cada afirmação numérica é rastreável até a fonte, e o
    score final é <strong>descontado por pendências</strong> de evidência. Análise com 15% de
    fontes datadas não vale o mesmo que uma com 80%.
  </blockquote>

  <p>Três mecanismos impedem que o relatório seja apenas texto convincente:</p>
  <ul>
    <li><strong>Triagem antes do gasto</strong> — ideias sem público, dor ou resultado identificáveis
      são reprovadas no modelo barato. O pipeline completo não roda e não é cobrado.</li>
    <li><strong>Funil recalculado pelo sistema</strong> — TAM/SAM/SOM são reprocessados em Python a
      partir do bloco <code>FUNIL:</code>. As faixas calculadas sobrescrevem qualquer número
      divergente do texto, e o break-even é conferido contra o <strong>cenário pessimista</strong>,
      não contra o base.</li>
    <li><strong>Auditoria adversarial</strong> — uma fase recebe as anteriores rotuladas como
      material de terceiro, para revisar sem complacência com o próprio texto. Se ela não roda,
      isso vira pendência bloqueante.</li>
  </ul>

  <hr>

  <h2>⚙️ Fases da Metodologia</h2>
  <table>
    <tr><th>#</th><th>Fase</th><th>Entregável</th></tr>
    <tr><td>0</td><td><strong>Triagem</strong></td><td>Nota de clareza 0–10; abaixo do corte, reprova sem rodar as fases</td></tr>
    <tr><td>1</td><td><strong>Clareza do Produto</strong></td><td>Problema central, transformação, nicho primário/secundário</td></tr>
    <tr><td>2</td><td><strong>Análise de Mercado</strong></td><td>TAM, SAM, SOM auditáveis + curva de tendência</td></tr>
    <tr><td>3</td><td><strong>Análise de Concorrência</strong></td><td>Mapa competitivo, gaps, Proposta Única de Valor</td></tr>
    <tr><td>4</td><td><strong>Validação de Demanda</strong></td><td>Palavras-chave reais, intensidade da dor, ticket médio</td></tr>
    <tr><td>5</td><td><strong>Viabilidade de Negócio</strong></td><td>Estrutura de custos, break-even, pricing, escalabilidade</td></tr>
    <tr><td>6</td><td><strong>Prova Social</strong></td><td>Sinais de engajamento, influenciadores, estratégia de pré-lançamento</td></tr>
    <tr><td>7</td><td><strong>Riscos &amp; Mitigação</strong></td><td>Top 3 riscos + <strong>MVP de menor custo</strong> para testar a hipótese</td></tr>
    <tr><td>8</td><td><strong>Auditoria Interna</strong></td><td>Revisão adversarial das fases anteriores</td></tr>
  </table>
  <p><em>A lista autoritativa é <code>prompts.FASES</code>; a CLI e o relatório derivam a contagem dela.</em></p>

  <hr>

  <h2>🧠 Arquitetura</h2>
  <pre><code>main.py               <span class="comment"># CLI: entrada, persistência do relatório, exit codes</span>
src/
├─ config.py          <span class="comment"># chaves, modelos, orçamento, limites de busca</span>
├─ prompts.py         <span class="comment"># FASES, templates, contrato de avaliação, system blocks</span>
├─ llm.py             <span class="comment"># client, usage/custo, research() com require_web</span>
├─ fontes.py          <span class="comment"># Fonte: URL + data + janela de recência</span>
├─ evidencias.py      <span class="comment"># scoring de confiança, URLs sem data, auditoria</span>
├─ funil.py           <span class="comment"># parse de TAM/SAM/SOM e break-even</span>
├─ mercado.py         <span class="comment"># cenários, amplitude, veredicto de ponto de equilíbrio</span>
├─ rubrica.py         <span class="comment"># notas por critério, eliminatórios, faixas de veredicto</span>
├─ pendencias.py      <span class="comment"># registro de lacunas, níveis, penalidade no score</span>
└─ pipeline.py        <span class="comment"># orquestração, triagem, budget guard, degradação</span></code></pre>

  <h3>Decisões de engenharia</h3>
  <ul>
    <li>🎯 <strong>Peso temporal da evidência</strong> — fontes sem data de publicação são registradas
      como pendência de recência não auditável; a proporção de afirmações datadas entra no
      cabeçalho do relatório.</li>
    <li>🔁 <strong>Degradação por fase</strong> — sem evidência externa, a fase é refeita com o
      <em>system</em> <strong>sem web</strong> e o texto recebe selo
      <code>SEM EVIDÊNCIA EXTERNA</code>. Pedir evidência a quem não pode buscar é convite à
      confabulação.</li>
    <li>🛡️ <strong>Budget guard</strong> — o gasto é conferido antes de cada fase e a execução é
      <strong>interrompida</strong> ao passar de <code>VALIDADOR_ORCAMENTO</code>, em vez de
      sangrar crédito silenciosamente.</li>
    <li>📐 <strong>Contrato de saída com retry</strong> — o avaliador precisa abrir com
      <code>NOTAS:</code> e todos os critérios. Duas tentativas; se ambas falharem, não há score
      auditável e o relatório diz isso.</li>
    <li>🧪 <strong>Núcleo puro e testável</strong> — o pipeline não toca disco (quem grava é a CLI)
      e aceita LLM injetável, então roda sem gastar tokens em testes futuros.</li>
  </ul>

  <hr>

  <h2>🚀 Stack &amp; Competências</h2>
  <p class="stack-tags">
    <code>Python</code> · <code>LLM Orchestration</code> · <code>Prompt Engineering</code> ·
    <code>RAG (Retrieval-Augmented Generation)</code> · <code>AI Agents</code> ·
    <code>Web Search API</code> · <code>Anthropic API</code> · <code>Data-Driven Decision Making</code> ·
    <code>Market Research</code> · <code>TAM/SAM/SOM</code> · <code>Product Discovery</code> ·
    <code>Growth Marketing</code> · <code>CRO</code> · <code>Clean Architecture</code> · <code>Git</code>
  </p>

  <hr>

  <h2>🏁 Como Executar</h2>
  <pre><code>git clone https://github.com/&lt;seu-usuario&gt;/proofkit.git
cd proofkit

python -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env # preencha ANTHROPIC_API_KEY

python main.py --ideia "Mentoria de tráfego pago para dentistas"
python main.py # modo interativo (stdin)
python main.py --sem-triagem -q # pula o corte inicial, imprime só o caminho</code></pre>

  <p>Relatórios em <code>relatorios/AAAAMMDD-HHMMSS-slug.md</code>.</p>

  <table>
    <tr><th>Flag</th><th>Efeito</th></tr>
    <tr><td><code>--ideia</code></td><td>Ideia em uma linha; omitido, lê do stdin</td></tr>
    <tr><td><code>--sem-triagem</code></td><td>Executa todas as fases sem o corte de clareza</td></tr>
    <tr><td><code>--out</code></td><td>Pasta de destino dos relatórios</td></tr>
    <tr><td><code>-q</code>, <code>--quiet</code></td><td>Sem progresso; imprime apenas o caminho do arquivo</td></tr>
  </table>

  <p>
    Exit codes: <code>0</code> sucesso · <code>1</code> falha de LLM ou de gravação ·
    <code>2</code> configuração ou ideia inválida · <code>130</code> interrompido.
  </p>

  <h3>Variáveis de ambiente</h3>
  <table>
    <tr><th>Variável</th><th>Função</th></tr>
    <tr><td><code>ANTHROPIC_API_KEY</code></td><td>Credencial da API (obrigatória)</td></tr>
    <tr><td><code>VALIDADOR_ORCAMENTO</code></td><td>Teto de gasto por validação, em US$</td></tr>
    <tr><td><code>VALIDADOR_MAX_WEB</code></td><td>Máximo de buscas web</td></tr>
    <tr><td><code>VALIDADOR_TRIAGEM_CORTE</code></td><td>Corte 0–100 da triagem</td></tr>
  </table>

  <hr>

  <h2>🗺️ Roadmap</h2>
  <ul class="roadmap">
    <li class="done">Núcleo das fases + triagem</li>
    <li class="done">Camada de scoring de evidência e pendências</li>
    <li class="done">Funil TAM/SAM/SOM recalculado em Python</li>
    <li>Suíte de testes automatizados (pytest)</li>
    <li>Dashboard web do relatório</li>
    <li>Exportação em PDF</li>
    <li>Cache persistente de buscas</li>
  </ul>

  <hr>

  <h2>📄 Licença</h2>
  <p>Distribuído sob a licença <strong>MIT</strong>. Veja <a href="LICENSE"><code>LICENSE</code></a>.</p>

  <footer>
    Desenvolvido por <strong>Carlos</strong> · Fortaleza, CE 🇧🇷<br>
    <a href="https://www.linkedin.com/in/andreorganizacional/">LinkedIn</a> ·
    <a href="mailto:andre.tavora3@gmail.com">E-mail</a>
  </footer>

</div>
</body>
</html>
