# APEXIUM Studio — site, aplicativo e modo sem programação

O **APEXIUM Studio** é uma interface web responsiva, sem cadastro e gratuita para explorar dados públicos da Fórmula 1. Ele é também um **Progressive Web App (PWA)**, instalável em aparelhos compatíveis com navegadores modernos. Não é um APK nativo, nem um executável Windows.

## Acesso público

Após habilitar o GitHub Pages no repositório e a automação de deploy passar:

**https://mukasanches.github.io/APEXIUM/**

Se o link não abrir, acesse **Settings → Pages → Build and deployment → Source: GitHub Actions** no GitHub e execute novamente o workflow **Site and App — Quality + Pages**. O workflow não tem credenciais para habilitar Pages em nome do dono do repositório quando o serviço ainda está desligado.

## O que qualquer pessoa consegue fazer

1. **Visão geral:** selecionar uma temporada, consultar etapas, liderança e classificação.
2. **Campeonato:** alternar classificação de pilotos e equipes, visualizar os pontos.
3. **Calendário:** conferir etapas, circuitos, países e horários locais, além de pesquisar.
4. **Race Lab:** escolher uma corrida e uma das **20 análises descritivas** sobre tempos, pneus, boxes, setores, posições, condições, telemetria e duas comparações diretas.
5. **Telemetry Studio:** selecionar corrida, piloto e volta para exibir gráficos de velocidade, acelerador, freio e RPM usando amostras reais disponibilizadas pela OpenF1.
6. **Data Explorer:** consultar famílias de recursos OpenF1/Jolpica sem escrever código e exportar JSON/CSV.
7. **Sobre:** consultar limites metodológicos e termos dos provedores.

APEXIUM utiliza dados de terceiros e respeita seus limites. O aplicativo não finge ter informações em tempo real quando a API exige assinatura. Ao selecionar telemetria no laboratório, a consulta de alta frequência é **deliberadamente limitada a uma volta**, evitando downloads excessivos.

## Instalar como aplicativo

- **Windows / macOS / Linux (Chrome e Edge):** abra o site e procure `Instalar aplicativo` na barra do navegador; também há um botão de orientação no site.
- **Android (Chrome):** abra o menu do navegador e escolha `Instalar app` ou `Adicionar à tela inicial`, conforme o navegador.
- **iOS (Safari):** abra o menu Compartilhar e escolha `Adicionar à Tela de Início`.

O app pode manter a interface em cache para carregar offline, mas **consultas às APIs dependem de internet**, exceto respostas que ainda estejam armazenadas pelo SDK. Não há uma base de dados offline completa incluída.

## Executar localmente para desenvolver

```bash
# Requer Node.js >= 20 para o script de build/preview (o SDK aceita Node >= 18)
git clone https://github.com/MukaSanches/APEXIUM.git
cd APEXIUM
node scripts/build-site.mjs
node scripts/serve-site.mjs
```

Acesse http://127.0.0.1:4173/ . O build copia somente os arquivos públicos para `dist/site`, incluindo o SDK JavaScript. A publicação oficial é feita pelo GitHub Actions, sem segredos de API no frontend.

## Testes e critérios de qualidade

```bash
# 20 testes de cálculos e estrutura web (Node.js)
node --test tests/site.test.mjs

# Testes existentes do SDK JavaScript
cd sdk/javascript && npm test && cd ../..

# Teste real de interface no Chromium, respostas das APIs simuladas
python -m pip install playwright
python -m playwright install chromium
python -m unittest discover -s tests -p browser_smoke.py -v
```

O workflow **Site and App — Quality + Pages** exige testes de cálculos e cenários completos de navegador, cobrindo navegação, rankings, calendário, laboratório, telemetria, PWA, exportação CSV/JSON e viewport móvel.

**O teste de interface utiliza respostas controladas das APIs.** Esse teste mede o software, mas não verifica a disponibilidade das APIs externas no momento da execução. Antes de declarar produção estável, ainda precisamos testar os endpoints reais, verificar termos/licenças e executar auditoria de acessibilidade.

## Arquitetura e segurança

- Site estático: HTML sem framework obrigatório, CSS responsivo, JavaScript ESM.
- Dados: SDK JavaScript do repositório, usando `fetch` e cache em memória.
- Matemática: `site/analytics.js`, 20 algoritmos puros testáveis.
- PWA: `site/manifest.webmanifest`, service worker e ícones 192/512 px.
- Build: `scripts/build-site.mjs` (sem bundler ou dependências externas).
- Deploy: workflow GitHub Pages com permissão mínima.
- Tabelas inserem dados de terceiros com `textContent`, evitando HTML arbitrário.
- Sessões de telemetria restringem consulta por piloto e intervalo de datas.

APEXIUM não é afiliado à F1, FIA, OpenF1 ou Jolpica. Consulte as condições de uso dos provedores antes de publicar redistribuições ou usar comercialmente os dados.
