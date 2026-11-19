# AWS e EKS

A referência operacional de **19/11/2026** é o cluster **`eks-store`**, em **US East (Ohio), `us-east-2`**, com as seis aplicações e o RabbitMQ no namespace **`store`**. O NLB expõe o gateway; os demais serviços e o PostgreSQL ficam privados. Esta configuração substitui o roteiro de preparação de 16/11, que ainda propunha o RDS e o terceiro nó.

## Recursos e rede

| Componente | Configuração |
|---|---|
| EKS | Plano de controle gerenciado do `eks-store` |
| Nós | Três EC2 `t2.small`, distribuídos em duas zonas de disponibilidade |
| Horário dos nós | Desligados de 23:59 a 06:00, horário de Brasília; a recriação pode alterar a distribuição dos pods |
| Entrada da aplicação | Um NLB, associado ao Service `gateway-public` |
| Serviços internos | `gateway`, `auth`, `account`, `product`, `order` e `exchange` em `ClusterIP`, porta 8080 |
| Banco | RDS PostgreSQL privado, `db.t4g.micro`, Single-AZ, 20 GiB gp3 |
| Isolamento do banco | Usuário e schema próprios para account, product e order; conexões com TLS |
| Saída | Dois NAT Gateways, um por zona; permitem, por exemplo, o acesso do exchange à PTAX |
| Broker | RabbitMQ 4.2 no cluster, com Service interno e armazenamento `emptyDir` |
| Imagens | Seis repositórios ECR; Deployments usam digest da imagem |

Os cinco serviços Java começam com uma réplica, assim como o exchange. O [HPA do gateway](load-testing.md) é aplicado para o teste e removido no fim, podendo chegar a três réplicas conforme a capacidade. O HPA cria pods; não cria nós. A agenda noturna dos nós não elimina as cobranças do plano de controle, banco, NATs, discos e NLB. Veja [custos e SLA](costs.md).

## Consultar o ambiente

Use uma identidade AWS autorizada. O comando abaixo configura apenas o acesso local ao cluster existente:

```bash
aws eks update-kubeconfig --name eks-store --region us-east-2 --alias eks-store
kubectl --context eks-store get nodes -o wide
kubectl --context eks-store -n store get deployments,pods,services
kubectl --context eks-store -n store top pods
kubectl --context eks-store -n store get hpa
```

Confirme o destino antes de executar comandos de alteração. Durante o horário noturno, a ausência de nós de aplicação não significa que o plano de controle foi excluído.

## Health-checks e probes

Os caminhos abaixo são os implementados nos serviços; account, product e order usam o nome no plural.

| Serviço | Startup e liveness, porta 8080 | Readiness | Métricas internas |
|---|---|---|---|
| [Gateway](services/gateway.md) | `/gateway/health-check` | `/actuator/health/readiness`, 9091 | `gateway-metrics:9091/actuator/prometheus` |
| [Auth](services/auth.md) | `/auth/health-check` | `/actuator/health/readiness`, 9091 | `auth-metrics:9091/actuator/prometheus` |
| [Account](services/account.md) | `/accounts/health-check` | `/actuator/health/readiness`, 9091 | `account-metrics:9091/actuator/prometheus` |
| [Product](services/product.md) | `/products/health-check` | `/actuator/health/readiness`, 9091 | `product-metrics:9091/actuator/prometheus` |
| [Order](services/order.md) | `/orders/health-check` | `/actuator/health/readiness`, 9091 | `order-metrics:9091/actuator/prometheus` |
| [Exchange](services/exchange.md) | `/exchange/health-check` | `/ready`, 8080 | `exchange:8080/metrics` |

Os health-checks retornam 200 sem corpo enquanto o processo atende HTTP. São chamados diretamente pelo Kubernetes, sem token. O gateway só libera seu próprio health-check como rota pública aberta; os dos outros serviços podem exigir autenticação ou ser bloqueados quando acessados através dele. Um health-check não comprova a disponibilidade de todas as dependências de negócio.

Para verificar localmente o gateway, sem criar outra entrada pública:

```bash
kubectl --context eks-store -n store port-forward svc/gateway 18080:8080
# Em outro terminal:
curl -i http://127.0.0.1:18080/gateway/health-check
```

## Configuração e entrega

Cada serviço recebe os valores não sensíveis em `<serviço>-config`. Os segredos do banco, da assinatura JWT e do broker ficam em Secrets, preparados separadamente dos releases. O RDS aceita a rede autorizada dos nós; credenciais e schemas são separados por serviço. O banco e o broker não são publicados pelo NLB.

O caminho de release é o [GitHub Actions de cada serviço, com ECR e OIDC](ci-cd.md). As pipelines atualizam a imagem por digest e aguardam o rollout. Não criam o RDS, não aumentam o node group e não sobrescrevem os Secrets. Os scripts Python do agregador permanecem como ferramentas de laboratório e preparação, e não são um segundo processo de release de produção.

## Mensageria e capacidade

No order, `MESSAGING_ENABLED=true` e `ORDER_WORKER_ENABLED=true` habilitam relay e consumidor. O cache Redis de order permanece desligado; no exchange, Redis e eventos opcionais permanecem desligados, com o cache em memória PTAX ativo. O RabbitMQ é mantido no cluster e sua instalação é separada do deploy da aplicação.

Os nós `t2.small` têm limites de CPU, memória, pods e créditos de CPU. Antes de gravar, confirme espaço para as réplicas do gateway. O [roteiro de carga](load-testing.md) explica a calibração e os limites. Não aumente a capacidade apenas para reproduzir um exemplo de máximo de réplicas.

Com uma réplica, rollouts e falhas de nó podem causar indisponibilidade. O RabbitMQ com `emptyDir` perde mensagens em trânsito se seu armazenamento for recriado. RDS Single-AZ e ausência de réplicas distribuídas também limitam a disponibilidade; os [cenários de melhoria](costs.md) registram o impacto financeiro.

Fontes: os READMEs e manifests ligados nas [páginas dos serviços](index.md#navegar-pela-entrega), as [evidências EDA de 18/11](mensageria.md), a [calibração de carga de 18/11](load-testing.md) e o [levantamento de custos](costs.md).
