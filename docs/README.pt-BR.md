# APEXIUM — Guia em português

**APEXIUM** é um kit de desenvolvimento open-source para acessar dados reais da Fórmula 1 por Python e JavaScript.

**Estado:** código-fonte v1.0.0 alpha, ainda não publicado no PyPI ou npm. O projeto não reivindica recordes de adoção, desempenho ou tamanho.

## Instalação local

~~~bash
git clone https://github.com/MukaSanches/APEXIUM.git
cd APEXIUM
python -m pip install -e .
~~~

## Primeiros dados reais

~~~python
from apexium import Apexium

f1 = Apexium()
print(f1.openf1.meetings(year=2025).records[:2])

brasil = f1.race(2025, "Brazil")
print(brasil.results().records[:3])
print(brasil.pace_analysis()[:5])

historico = f1.jolpica.driver_standings(2025)
print(historico.records[0]["DriverStandings"][:3])
~~~

## JavaScript

~~~js
import { Apexium, racePace } from "./sdk/javascript/index.js";

const f1 = new Apexium();
const race = f1.race(2025, "Brazil");
const laps = await race.laps();
console.log(racePace(laps));
~~~

## O que já existe

- 18 famílias de endpoints OpenF1, incluindo telemetria, posições, voltas, boxes, pneus, clima e direção de prova.
- 13 famílias de endpoints Jolpica para histórico, resultados, classificações, pilotos e construtores.
- Métodos de alto nível para localizar o GP e a sessão de corrida.
- Cache SQLite em Python e cache de memória no JavaScript.
- Exportação JSON, CSV e Parquet opcional (Python).
- Análises descritivas, diagnóstico de dados e interface de terminal.
- Ponte opcional para a biblioteca FastF1.

## Limitações importantes

- OpenF1 tem dados detalhados desde 2023; consulta ao vivo exige acesso autorizado pago.
- Jolpica cobre temporadas históricas, mas tem limites de requisições.
- A biblioteca não fornece direitos comerciais sobre dados de terceiros.
- Rankings de ritmo não são corrigidos por combustível, pneus, tráfego ou clima.
- A telemetria pode apresentar lacunas. O programa não inventa dados ausentes.

Consulte o [README principal](../README.md), a [documentação da API](api.md) e as [orientações de contribuição](../CONTRIBUTING.md).
