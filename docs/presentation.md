# Apresentação

A apresentação tem **1 minuto e 50 segundos**, com dez segundos de margem até o limite de dois minutos. O roteiro combina quatro slides com três trechos reais do EKS: visão dos pods, carga/HPA e mensageria. João grava e edita esses trechos no DOC-04.

**Vídeo final:** aguardando gravação, edição e publicação no DOC-04. O link de reprodução será incluído aqui quando estiver disponível.

## Slides

- [Baixar PowerPoint editável](assets/apresentacao.pptx)
- [Abrir a versão PDF](assets/apresentacao.pdf)

Os quatro slides cobrem introdução, arquitetura, o gargalo de mensageria e a conclusão. As notas do PowerPoint identificam os pontos de entrada das demonstrações. Os arquivos desta página ficam disponíveis para o João pelo repositório e, após a publicação, pelo próprio MkDocs.

## Roteiro cronometrado

| Tempo | Imagem | Narração |
|---|---|---|
| 00:00–00:10 | Slide 1: introdução | “Nossa loja reúne seis microsserviços independentes no EKS. Vamos mostrar a arquitetura, o escalonamento e a confirmação assíncrona dos pedidos.” |
| 00:10–00:30 | Slide 2: arquitetura | “O NLB recebe o tráfego e encaminha ao gateway. O auth valida a identidade com apoio do account. Product e order usam schemas próprios no RDS privado; exchange fornece as cotações. GitHub Actions publica no ECR e implanta no EKS com OIDC.” |
| 00:30–00:40 | Trecho A, gravado pelo João: pods do namespace `store` | “Aqui estão os seis serviços e o RabbitMQ no namespace store. Só o gateway tem entrada pública; os outros serviços ficam internos.” |
| 00:40–00:58 | Trecho B, gravado pelo João: k6, HPA e pods | “O k6 gera carga no health-check do gateway, sem atingir o Banco Central. O HPA acompanha a CPU e aumenta as réplicas conforme a capacidade. Este trecho resume a execução; a documentação mantém a configuração e os resultados completos.” |
| 00:58–01:25 | Slide 3 por 7 s, depois trecho C por 20 s: criação do pedido, outbox, fila e consumidor | “O gargalo escolhido foi a confirmação de pedidos. Pedido e evento entram na mesma transação. A outbox permite responder antes do processamento. O relay entrega ao RabbitMQ, e o consumidor deduplica pelo evento. Com o broker indisponível, a outbox aguarda; mensagens inválidas vão para a DLQ.” |
| 01:25–01:50 | Slide 4: conclusão, responsabilidades e próximos passos | “Order e exchange começaram com adventurescumm até 16 de novembro. João assumiu os outros quatro serviços, a infraestrutura e a integração. O uso de IA está declarado nos READMEs. Os próximos passos são persistir o RabbitMQ, ampliar a disponibilidade e melhorar a revogação dos tokens. Código e evidências estão na documentação.” |

As falas somam 220 palavras. Ensaie a locução com as transições e mantenha a versão final entre um e dois minutos. Se ultrapassar dois minutos, corte pausas e detalhes das falas, preservando os três trechos reais e a atribuição de autoria.

## Trechos que entram na edição

| Trecho | Duração no vídeo | O que o João precisa capturar |
|---|---|---|
| A — ambiente | 10 s | `kubectl -n store get pods -o wide`, com os seis serviços e RabbitMQ visíveis |
| B — carga | 18 s | k6 em execução, coluna de CPU do HPA e criação de réplicas; seguir o [roteiro de carga](load-testing.md) |
| C — mensageria | 20 s | `POST /orders` com 201, evento aguardando quando o broker para, recuperação e confirmação; mostrar a DLQ com payload inválido conforme a [demonstração EDA](mensageria.md) |

O teste de carga completo dura vários minutos e a demonstração EDA também é maior que o trecho final. Use cortes ou aceleração identificada na tela. Não faça a edição sugerir que toda a rampa e a recuperação ocorreram em poucos segundos, nem apresente os números de calibração como resultados de uma gravação ainda não feita.

## Conferência antes de entregar

1. Conferir se os nós estão ativos (`kubectl get nodes`); desde 20/11 eles não desligam mais à noite.
2. Conferir legibilidade do terminal, nomes dos serviços e números do HPA; ocultar tokens, senhas e dados pessoais.
3. Usar as declarações de [autoria](team.md), incluindo o apoio de IA informado nos READMEs.
4. Exportar o vídeo final entre 1 e 2 minutos e testar a reprodução sem depender da sessão do autor.
5. Incluir o link definitivo no começo desta página e abrir a revisão da alteração.

Prazo da entrega: **20/11/2026 às 23:59** (confirmado pelo João).

Fontes: [arquitetura](architecture.md), [mensageria](mensageria.md), [teste de carga](load-testing.md) e os READMEs ligados nas [páginas dos serviços](index.md#navegar-pela-entrega).
