# Validação local — 16/11/2026

Este registro preserva as execuções locais de 16/11. As menções a RDS, capacidade e publicação ainda pendentes descrevem aquela data. O estado de referência de 19/11 está em [AWS e EKS](deployment.md); evidências posteriores estão em [mensageria](mensageria.md) e [teste de carga](load-testing.md).

## Fluxo funcional e testes automatizados

Os cinco projetos Java passaram no `mvn verify` com JDK 25: 53 testes aprovados e um teste de infraestrutura opcional ignorado. A execução Python/Bash em container Linux teve 76 testes aprovados e três ignorados, incluindo verificações que dependem de Redis/RabbitMQ ou kubectl real. Os três testes do renderer integrado também passaram. A documentação compila com `mkdocs build --strict` e os workflows passaram no actionlint.

O teste funcional passou pelo gateway no Compose e por port-forward no Kubernetes local. Foram verificados cadastro, login, JWT inválido, bloqueio de rotas internas, sobrescrita de identidade forjada, criação de produto, pedido de duas unidades a USD 10,12, total de USD 20,24 e isolamento entre contas. No Compose também passou uma conversão real para BRL. A carga usa USD/USD e não chama o provedor externo de câmbio.

## Carga com Compose

Docker Desktop com containers Linux no Windows; engine com aproximadamente 7,6 GiB de memória disponível. Os resultados abaixo são locais e não estimam a capacidade do EKS.

| Perfil | Duração | Usuários virtuais | Requisições | Falhas na fase de carga | p95 na fase de carga |
|---|---|---|---:|---:|---:|
| smoke | 15 s | 1 | 350 | 0% | 14,17 ms |
| ramp | 7 min | até 30 | 232.583 | 0% | 5,67 ms |

A rampa registrou vazão média de aproximadamente 553 requisições/s, incluindo setup e encerramento. O número total de requisições inclui cinco operações de preparação/limpeza; latência e taxa de falhas marcadas `phase:load` referem-se apenas às leituras autenticadas de produto, pedido e câmbio. O aquecimento da JVM e diferenças no perfil influenciam os resultados; não compare diretamente as duas linhas como ganho de uma alteração de código.

Arquivos locais preservados: `artifacts/k6-smoke.json` e `artifacts/k6-ramp-compose.json`. O teste não aumentou a carga até saturação; esses valores não representam a capacidade máxima.

## HPA no Kubernetes local

Perfil Minikube isolado `store-local`, namespace `store-demo`, quatro CPUs e 4.096 MiB configurados, Kubernetes 1.37 e Metrics Server. Foram usadas as mesmas seis imagens construídas e testadas localmente, com um PostgreSQL local separado por schemas. A carga roda dentro do cluster pelo Service `gateway`, permitindo distribuição entre réplicas.

Foi observado o ciclo completo **1 → 2 → 3 → 1 réplicas** do gateway: expansão por CPU acima do alvo de 50% e redução automática após a carga e a janela de estabilização. As três réplicas ficaram prontas durante a carga, e o ambiente terminou com uma réplica pronta e nenhum reinício das aplicações. A sequência está registrada no arquivo local `artifacts/hpa-timeline.local.jsonl`.

A rampa de sete minutos no Minikube concluiu com **232.298 requisições**, **0% de falhas na fase de carga**, **p95 de 5,25 ms** e vazão média aproximada de **549 requisições/s**. Todos os thresholds passaram. O resumo está em `artifacts/k6-ramp-minikube.json`; o log completo está em `artifacts/k6-minikube.local.log`. A captura de eventos fica em `artifacts/hpa-events.local.json`.

O contexto padrão do kubectl permaneceu apontado para o EKS; todos os comandos de escrita desta demonstração usaram explicitamente o contexto Minikube. Nenhuma alteração foi aplicada à AWS.

Ao encerrar, o perfil Minikube de demonstração foi parado preservando seus dados. O Compose foi restaurado, o teste funcional passou novamente, os seis alvos do Prometheus estavam `up` e o dashboard Grafana `store-overview` foi validado com seus quatro painéis. O gateway está em `http://127.0.0.1:8080`, Prometheus em `http://127.0.0.1:9090` e Grafana em `http://127.0.0.1:3000`; a senha Grafana está no `.env` local.

## O que falta para a entrega externa

- Gravar o vídeo mostrando carga, HPA e pods, seguindo o [roteiro](load-testing.md).
- Salvar os cenários e o link compartilhável na AWS Pricing Calculator com as [premissas de custos](costs.md).
- Publicar os commits dos serviços alterados e atualizar seus gitlinks no agregador.
- Se a implantação AWS for retomada, autorizar banco/capacidade, aplicar a preparação documentada e repetir os testes no EKS. O usuário optou por manter essa etapa preparada, sem novos gastos.

EKS já está em uso como plataforma Kubernetes gerenciada. RDS continua sendo uma proposta; a validação local não comprova uso de RDS ou capacidade da infraestrutura AWS.

## Revisão do provedor de câmbio — BACEN/PTAX

Após a orientação do professor, exchange passou a consultar diretamente `olinda.bcb.gov.br`, usando a última PTAX de fechamento disponível em uma janela de dez dias. O contrato `/exchanges/{source}/{target}` foi preservado. A revisão passou em 40 testes do serviço/configuração local; o teste opcional com Redis/RabbitMQ reais não foi executado nesta revisão. Foram cobertos inversão, pares cruzados na mesma data, boletins fora de ordem, falta de fechamento recente, moedas sem cobertura e falhas do BACEN.

O exchange foi reconstruído no Compose e o teste funcional com conversão real de pedido para BRL passou. Consultas reais USD/BRL, BRL/USD e USD/EUR retornaram 200. Também foi obtida uma cotação PTAX válida a partir do pod auth já existente no EKS, confirmando acesso ao BACEN pela rede AWS desse cluster. Essa consulta não alterou Deployments nem criou recursos AWS; a nova imagem de exchange continua apenas local e depende de publicação futura.

As medições de carga e HPA anteriores usam USD/USD e não medem a latência do BACEN. A cotação PTAX é de fechamento, não uma taxa de mercado em tempo real; veja a [documentação do serviço](https://github.com/projeto-microservicos/exchange-service) quando os commits desta revisão forem publicados.
