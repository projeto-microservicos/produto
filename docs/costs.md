# Custos e responsabilidades

As faturas seguem a conta ou organização que hospeda o recurso. O rateio entre integrantes depende de um acordo da equipe; criar um workflow não define quem deve pagar ao grupo.

| Recurso | Quem recebe a cobrança | Condição |
|---|---|---|
| Repositório GitHub e submodules | Titular/organização, conforme o plano | Submodules são referências Git e não exigem um serviço pago próprio |
| MkDocs | Não exige serviço hospedado pago próprio | Gera arquivos estáticos localmente ou no CI |
| GitHub Pages | Titular/organização do repositório | Disponível para repositórios públicos no GitHub Free; repositórios privados exigem plano compatível |
| GitHub Actions | Titular/organização do repositório | Runners padrão são gratuitos em repositórios públicos; em privados há franquias e eventual cobrança; armazenamento tem regras próprias |
| EKS, nós, discos e rede | Conta AWS que hospeda os recursos | Cobrança continua enquanto existirem recursos faturáveis |
| ECR | Conta AWS do registro | Armazenamento e outros consumos seguem a tabela do serviço |
| RDS | Conta AWS do banco | Provisionar somente após aprovação do responsável |
| Redis/RabbitMQ no cluster | Conta AWS do cluster | Consomem CPU, memória e eventualmente discos/rede; podem exigir mais nós |

Para documentação pública, use o domínio padrão `github.io` e runners padrão do Actions. Não é necessário contratar EC2, S3 ou RDS para servir o MkDocs no Pages. Domínio próprio e planos pagos são decisões separadas.

O responsável pela conta AWS aprova RDS e qualquer aumento de capacidade. A equipe deve combinar previamente orçamento, eventual rateio e data de desligamento dos recursos. Não há valor mensal fixado aqui: ele depende de região, tipos/tamanhos, horas, armazenamento e rede.

Fontes oficiais consultadas em 16/11/2026:

- [GitHub Pages e planos suportados](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Cobrança do GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Preços do EKS e recursos associados](https://aws.amazon.com/eks/pricing/)
- [Preços do ECR](https://aws.amazon.com/ecr/pricing/)
- [Preços do RDS](https://aws.amazon.com/rds/pricing/)
