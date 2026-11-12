# Como funciona

Resumo para estudar antes de uma entrevista técnica: o que cada parte faz, por que foi feita assim e as perguntas que costumam aparecer.

## 1. Visão geral

```
detector_golpe/rules.py   núcleo: regras, veredito e comparação entre vagas (só biblioteca padrão)
detector_golpe/cli.py     linha de comando: lê JSON e imprime uma linha por vaga
detector_golpe/api.py     API FastAPI: POST /analyze com um lote de vagas
streamlit_app.py          página web: cola um anúncio e vê os sinais
```

Toda a lógica fica em `rules.py`. Ele não sabe nada de HTTP, terminal ou tela. A CLI, a API e a página são cascas finas que chamam a mesma função `analyze`. Por isso dá para testar as regras sem subir servidor, e as três interfaces nunca discordam.

## 2. O caminho de uma análise

1. `analyze(jobs)` recebe uma lista de tuplas `(id, cargo, texto)`.
2. `batch_pairs(jobs)` compara as vagas entre si e devolve os pares com texto copiado (sinal A2).
3. Para cada vaga, `check(texto)`:
   - corta o texto onde a página começa a listar outras vagas ("Vagas similares", "Denunciar vaga");
   - junta espaços e separadores `|`;
   - roda as regras.
4. `decide(sinais)` conta os sinais por letra e devolve o veredito:
   - **CONFIDENCIAL**: qualquer C, e tem prioridade, porque sem saber a empresa não dá para confirmar nada;
   - **SUSPEITA**: qualquer G, ou dois A;
   - **ALERTA**: um A;
   - **ok**: nenhum sinal.
5. O resultado traz, para cada vaga, o veredito e a lista de sinais com código, trecho encontrado e significado.

## 3. As regras

**Sinais de golpe (G):**
- **G1** pega cobrança de curso, taxa, kit, uniforme ou exame. Golpe clássico: a "empresa" lucra com a taxa, não com o trabalho.
- **G2** pega contato fora do canal da empresa:
  - e-mail de domínio gratuito (gmail, hotmail);
  - link `wa.me` ou `t.me`;
  - e-mail disfarçado, como `nome(a )hotma il.c om`;
  - verbo de contato colado em WhatsApp ou Telegram ("chame no WhatsApp").
  
  "Atendimento aos clientes pelo WhatsApp" **não** conta: ali o WhatsApp é ferramenta de trabalho. Os testes `test_whatsapp_as_work_tool_is_not_a_signal` guardam esses casos.
- **G3** pega pedido de RG, CPF, dados bancários ou chave PIX ainda no anúncio.
- **G4** pega promessa de aprovação sem entrevista.

**Alertas (A):**
- **A1**: empresa confidencial junto com "contratação urgente".
- **A3**: salário acima de R$ 3.000 para ensino médio e trabalho remoto.
  - Numa faixa ("R$ 100,00 a R$ 4.000,00"), vale o piso.
  - Não conta quando o anúncio pede anos de experiência ou idioma avançado, porque aí o salário se explica.
- **A4**: texto com menos de 400 caracteres, exceto o aviso de "vaga não está mais disponível".
- **A5**: currículo por e-mail, WhatsApp ou telefone, ou link encurtado (bit.ly, forms.gle).
- **A6**: modelo não preenchido, como `[cidade]`, `lorem ipsum` ou o rodapé de documento interno colado.

**Empresa oculta (C):**
- "Empresa confidencial".
- Consultoria que fala por um "nosso cliente" sem dizer quem é.
- Empresa descrita só pelo ramo ("indústria do segmento alimentício").

O cuidado aqui é não confundir com atendimento ao cliente: "entregar a melhor experiência ao nosso cliente" é normal. Por isso a regra exige um verbo ou substantivo de seleção logo depois ("nosso cliente busca", "nosso cliente, localizado em").

## 4. Texto copiado entre vagas (A2)

Golpes costumam publicar o mesmo texto com cargos diferentes (Auxiliar Administrativo, Assistente Financeiro...) para pegar mais gente.

1. Cada texto vira um conjunto de **5-gramas de palavras**: todas as sequências de 5 palavras seguidas.
2. A semelhança entre dois textos é o **índice de Jaccard**: tamanho da interseção dividido pelo tamanho da união dos conjuntos.
3. Acima de 0,6, os textos são quase iguais.

Exceções:
- **Mesmo cargo** não conta: é a mesma vaga em outro site ou em outra filial.
- **Datas diferentes** não contam: é o texto institucional da empresa reaproveitado.
- **Mesmo bloco de salário e jornada** em vagas "confidenciais" conta mesmo com o resto diferente.

**Por que 5 palavras?** Com 1 ou 2, qualquer vaga da mesma área parece igual ("experiência com", "home office"). Com 5, só texto copiado de verdade casa.

**Custo:** compara todos os pares, O(n²). Para algumas centenas de vagas por dia é instantâneo. Com milhares, trocaria por MinHash/LSH, que agrupa textos parecidos sem comparar todos os pares.

## 5. A API

- **FastAPI com Pydantic.** Os modelos `Job` e `Batch` validam a entrada antes do código rodar:
  - texto vazio ou lista vazia devolve **422** automaticamente;
  - limites de tamanho (50 mil caracteres por texto, 500 vagas por lote) evitam que uma chamada trave o servidor.
- **`response_model`** documenta a saída. A página `/docs` (Swagger) sai de graça.
- **Lote, não vaga única.** O A2 precisa ver várias vagas juntas, então o endpoint recebe uma lista.
- **`/health`** existe para Docker e monitores saberem se o serviço está de pé.

## 6. Testes

- `tests/test_rules.py` usa `pytest.mark.parametrize` para rodar a mesma verificação com vários textos. Cada caso é um falso positivo ou falso negativo que já aconteceu, com dados inventados.
- `tests/test_api.py` usa o `TestClient` do FastAPI: chama a API sem subir servidor nem abrir porta.
- `tests/test_cli.py` usa `tmp_path` (arquivo temporário) e `capsys` (captura o que foi impresso).

Rodar: `uv run pytest`. São 61 testes e levam cerca de 1 segundo.

## 7. Docker e CI

- O `Dockerfile` copia primeiro só `pyproject.toml` e `uv.lock` e instala as dependências; depois copia o código. Assim, mudar uma linha de código não reinstala tudo: o Docker reaproveita a camada das dependências.
- O `compose.yaml` sobe dois serviços com a mesma imagem: a API (porta 8000) e a página (porta 8501).
- O GitHub Actions roda ruff, pytest e `docker build` a cada push. Se algo quebrar, o selo do README fica vermelho.

## 8. Perguntas prováveis

**Por que regras e não um modelo de IA?**
Não há base rotulada grande o bastante para treinar. Regras dão para explicar ("marcou porque pediu taxa de cadastro"). Também rodam sem custo, sem internet e em milissegundos. Uma IA poderia entrar depois como segunda opinião nos casos ALERTA.

**Como você sabe que funciona?**
Cada regra tem testes com casos que devem e que não devem disparar. Quando aparece um erro novo, o caso vira teste antes da correção.

**Qual o maior risco?**
Falso positivo em vaga legítima. Por isso o veredito é um aviso para a pessoa ler, não um bloqueio automático.

**O que você mudaria para escalar?**
- MinHash no A2.
- Regras em arquivo de configuração, para quem não programa poder ajustar.
- Log dos vereditos para medir quais regras mais acertam.

**Qual foi o papel da IA no projeto?**
As regras e os casos vieram do meu uso real. O Claude Code ajudou a organizar o código em pacote, escrever a API, a página e os testes. Revisei e rodei tudo.
