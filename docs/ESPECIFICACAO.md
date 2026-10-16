# PROMPT — SISTEMA RITA & JEAN FINANCE

## 1. Objetivo do projeto

Desenvolva um sistema web completo chamado **Rita & Jean Finance**, destinado à gestão financeira pessoal e compartilhada de um casal.

O sistema deverá permitir que duas pessoas acompanhem suas receitas, despesas, contas bancárias, cartões de crédito, dívidas, metas de economia e planejamento financeiro.

A aplicação deverá ser intuitiva, moderna, segura, responsiva e preparada para expansão.

O principal objetivo é permitir que o casal saiba:

- Quanto dinheiro recebe mensalmente.
- Quanto cada pessoa ganha e gasta.
- Quanto o casal gasta em conjunto.
- Quais despesas estão pagas ou pendentes.
- Quanto dinheiro está disponível.
- Quanto será necessário para pagar as próximas contas.
- Quanto pode ser economizado mensalmente.
- Qual será a situação financeira nos próximos meses.

## 2. Tecnologias utilizadas

### Backend
- Python 3.12 ou superior.
- FastAPI para desenvolvimento da API REST.
- SQLAlchemy para gerenciamento do banco de dados.
- Pydantic para validação dos dados.
- Alembic para migrações do banco.
- Autenticação utilizando JWT e senhas protegidas com hash seguro.

### Frontend
- HTML5 para estruturação.
- CSS3 para estilização.
- JavaScript para interatividade.
- Fetch API para comunicação com o backend.
- Chart.js para gráficos financeiros.
- Layout responsivo para computadores, tablets e celulares.

### Banco de dados
- SQLite durante o desenvolvimento.
- PostgreSQL para utilização em produção.
- Estrutura relacional com chaves primárias, estrangeiras e integridade dos dados.

### Arquitetura
Utilizar arquitetura modular, separando:

- Rotas e endpoints.
- Regras de negócio.
- Modelos do banco de dados.
- Schemas de validação.
- Serviços.
- Autenticação.
- Frontend.
- Testes.

O código deverá ser organizado e seguir boas práticas de programação.

## 3. Dashboard financeiro

Criar uma página inicial com indicadores financeiros atualizados conforme os registros.

### Cards principais

1. Receita total do casal.
2. Receita individual de Rita.
3. Receita individual de Jean.
4. Despesas totais do mês.
5. Despesas compartilhadas.
6. Despesas individuais.
7. Saldo disponível nas contas.
8. Faturas de cartões pendentes.
9. Contas a pagar.
10. Economia realizada no mês.
11. Saldo previsto no final do mês.
12. Percentual da renda comprometida.

### Gráficos

- Receitas versus despesas.
- Evolução financeira dos últimos 12 meses.
- Despesas por categoria.
- Comparativo de gastos entre os integrantes.
- Evolução do patrimônio.
- Despesas fixas versus variáveis.
- Distribuição dos gastos por forma de pagamento.

Adicionar filtros por mês, ano, integrante, categoria e conta bancária.

## 4. Gestão de usuários

O sistema deverá permitir o cadastro de usuários vinculados ao mesmo grupo familiar.

### Informações
- Nome completo.
- E-mail.
- Senha.
- Foto de perfil opcional.
- Data de cadastro.
- Status do usuário.

### Permissões

**Administrador:** gerencia integrantes, categorias, configurações e permissões.

**Integrante:** registra e acompanha suas movimentações financeiras conforme as permissões.

Cada lançamento deverá identificar seu responsável.

Permitir que uma despesa seja classificada como:

- Particular de Rita.
- Particular de Jean.
- Compartilhada pelo casal.

As despesas pessoais poderão ser privadas ou visíveis ao casal, conforme configuração de privacidade.

## 5. Cadastro de receitas

Criar uma página para registrar todas as entradas financeiras.

### Campos
- Descrição.
- Valor.
- Data de recebimento.
- Data prevista.
- Categoria.
- Responsável pelo recebimento.
- Conta bancária de destino.
- Tipo de receita.
- Status: prevista ou recebida.
- Recorrência.
- Observações.

### Categorias
- Salário.
- Horas extras.
- Décimo terceiro.
- Férias.
- Bonificações.
- Comissões.
- Trabalhos extras.
- Rendimentos.
- Reembolsos.
- Outras receitas.

Permitir receitas recorrentes e lançamentos futuros.

## 6. Gestão de despesas

Criar uma página para cadastrar e acompanhar os gastos.

### Campos
- Descrição.
- Valor.
- Data da compra.
- Data do vencimento.
- Data do pagamento.
- Categoria e subcategoria.
- Responsável pelo gasto.
- Responsável pelo pagamento.
- Conta ou cartão utilizado.
- Forma de pagamento.
- Tipo de despesa.
- Situação.
- Observações.
- Comprovante em anexo.

### Classificações

Por responsabilidade:
- Rita.
- Jean.
- Compartilhada.

Por tipo:
- Fixa.
- Variável.
- Eventual.

Por situação:
- Pendente.
- Paga.
- Vencida.
- Cancelada.

### Categorias sugeridas
- Moradia.
- Aluguel ou financiamento.
- Energia elétrica.
- Água.
- Internet.
- Supermercado.
- Alimentação.
- Transporte.
- Combustível.
- Saúde.
- Farmácia.
- Educação.
- Lazer.
- Restaurantes.
- Assinaturas.
- Veículo.
- Vestuário.
- Presentes.
- Pets.
- Impostos.
- Outros.

Permitir criar, editar, excluir e personalizar categorias.

## 7. Divisão de despesas do casal

Implementar um módulo específico para divisão de despesas.

### Modalidades

**Divisão igualitária:** cada integrante assume 50% da despesa.

**Divisão proporcional à renda:** o sistema calcula o percentual de participação com base nas receitas definidas para cada integrante.

**Divisão personalizada:** permitir configurar percentuais ou valores individuais.

### Exemplo

Uma despesa de supermercado de R$ 1.000,00 poderá ser dividida em:

- Rita: R$ 500,00.
- Jean: R$ 500,00.

Ou, utilizando uma divisão proporcional configurada de 40% e 60%:

- Rita: R$ 400,00.
- Jean: R$ 600,00.

O sistema deverá identificar quem efetivamente pagou a despesa e calcular eventuais valores de acerto entre os integrantes, evitando duplicar despesas no consolidado.

## 8. Gestão de cartões de crédito

Criar uma página exclusiva para cartões.

### Cadastro de cartões
- Nome do cartão.
- Instituição financeira.
- Titular.
- Limite total.
- Limite disponível.
- Dia de fechamento.
- Dia do vencimento.
- Conta de pagamento da fatura.
- Situação do cartão.

### Funcionalidades
- Registrar compras no crédito.
- Registrar compras parceladas.
- Distribuir parcelas nas respectivas faturas.
- Visualizar faturas abertas e fechadas.
- Consultar próximas faturas.
- Registrar pagamentos totais e parciais.
- Acompanhar limite disponível.
- Identificar compras por integrante.
- Exibir parcelas restantes.
- Permitir antecipação de parcelas.

O pagamento da fatura deverá liquidar a obrigação do cartão sem duplicar o valor da despesa nos relatórios.

## 9. Contas bancárias e carteiras

Permitir o cadastro de diferentes contas financeiras.

### Exemplos
- Conta corrente de Rita.
- Conta corrente de Jean.
- Conta conjunta.
- Conta poupança.
- Carteira em dinheiro.
- Conta de investimentos.

### Funcionalidades
- Cadastro de saldo inicial.
- Registro de entradas e saídas.
- Transferências entre contas.
- Histórico de movimentações.
- Conciliação de saldos.
- Saldo atual e previsto.

Transferências entre contas próprias não deverão ser consideradas receitas ou despesas.

## 10. Contas fixas e recorrentes

Criar um módulo para gerenciamento de compromissos recorrentes.

### Funcionalidades
- Despesas mensais.
- Despesas semanais.
- Despesas anuais.
- Receitas recorrentes.
- Repetição automática de lançamentos.
- Controle de vencimentos.
- Avisos de contas próximas do vencimento.
- Suspensão ou encerramento da recorrência.

Os lançamentos automáticos deverão evitar duplicidades.

## 11. Metas e objetivos financeiros

Criar uma página de planejamento de objetivos.

### Exemplos
- Reserva de emergência.
- Compra de veículo.
- Viagem.
- Reforma da casa.
- Compra de móveis.
- Investimentos.
- Quitação de dívidas.

### Campos
- Nome da meta.
- Valor desejado.
- Valor acumulado.
- Data de início.
- Prazo previsto.
- Responsável.
- Contribuição mensal planejada.

### Indicadores
- Percentual concluído.
- Valor restante.
- Tempo restante.
- Valor mensal necessário.
- Progresso financeiro em gráfico.

Permitir que os dois integrantes contribuam com valores diferentes.

## 12. Orçamento mensal

Criar uma página para planejamento financeiro por categoria.

### Funcionalidades
- Definir limite mensal de gastos.
- Registrar orçamento individual.
- Registrar orçamento compartilhado.
- Comparar planejado versus realizado.
- Identificar categorias com gastos excessivos.
- Visualizar percentual consumido.
- Alertar quando o limite estiver próximo.

Exemplo:

Orçamento do supermercado: R$ 1.500,00.

Valor utilizado: R$ 1.200,00.

Saldo do orçamento: R$ 300,00.

Consumo: 80%.

## 13. Gestão de dívidas e financiamentos

Cadastrar obrigações financeiras.

### Campos
- Descrição.
- Credor.
- Valor original.
- Saldo devedor.
- Taxa de juros.
- Quantidade de parcelas.
- Valor das parcelas.
- Vencimentos.
- Responsável.

### Funcionalidades
- Acompanhar parcelas pagas.
- Identificar parcelas em atraso.
- Calcular saldo restante conforme condições cadastradas.
- Registrar amortizações.
- Registrar quitação antecipada.
- Visualizar compromissos futuros.

## 14. Planejamento e projeção financeira

Criar uma funcionalidade para prever a situação financeira do casal.

O sistema deverá considerar:

- Saldo atual.
- Receitas previstas.
- Despesas fixas.
- Parcelamentos.
- Faturas.
- Contas futuras.
- Metas de economia.

Exibir projeções para 30, 60, 90 dias e 12 meses, com premissas identificadas.

Disponibilizar simulações como:

- Redução de despesas.
- Aumento de receitas.
- Nova compra parcelada.
- Criação de uma reserva.
- Antecipação de dívidas.

## 15. Calendário financeiro

Criar um calendário mensal com os compromissos.

Cada data deverá exibir:

- Contas a vencer.
- Contas pagas.
- Receitas previstas.
- Receitas recebidas.
- Vencimentos de cartões.
- Parcelamentos.

Permitir clicar em um dia para visualizar e editar os lançamentos.

## 16. Notificações e alertas

O sistema deverá gerar alertas para:

- Conta próxima do vencimento.
- Conta vencida.
- Fatura próxima do vencimento.
- Orçamento ultrapassado.
- Meta financeira atrasada.
- Saldo previsto insuficiente.
- Despesa compartilhada aguardando acerto.

As notificações aparecerão inicialmente dentro do sistema.

Preparar a arquitetura para integração futura com e-mail ou outros canais.

## 17. Relatórios financeiros

Criar uma página de relatórios com filtros avançados.

### Relatórios
- Receitas por período.
- Despesas por período.
- Gastos individuais.
- Gastos compartilhados.
- Despesas por categoria.
- Comparativo mensal.
- Fluxo de caixa.
- Contas pagas e pendentes.
- Cartões e parcelamentos.
- Acompanhamento de metas.
- Evolução do patrimônio.

Permitir exportação para Excel, CSV e PDF.

## 18. Interface e experiência do usuário

Criar um design moderno com:

- Menu lateral retrátil.
- Dashboard com cards.
- Gráficos interativos.
- Tabelas com pesquisa e filtros.
- Modais de cadastro.
- Botões de edição e exclusão.
- Ícones padronizados.
- Indicadores de progresso.
- Layout responsivo.
- Tema claro e escuro.
- Valores formatados em reais (R$).
- Datas no padrão brasileiro.

### Menu principal

1. Dashboard.
2. Receitas.
3. Despesas.
4. Cartões de crédito.
5. Contas bancárias.
6. Divisão do casal.
7. Orçamento mensal.
8. Metas financeiras.
9. Dívidas e financiamentos.
10. Calendário.
11. Relatórios.
12. Notificações.
13. Configurações.

## 19. Segurança e integridade

Implementar:

- Login autenticado.
- Hash seguro de senhas.
- Controle de acesso por usuário e grupo familiar.
- Proteção de endpoints.
- Validação de entradas.
- Proteção contra acesso a registros de outros grupos.
- Prevenção de SQL Injection.
- Armazenamento seguro de configurações sensíveis.
- Registro de alterações relevantes.
- Backup do banco de dados.
- Tratamento de erros.
- Proteção de anexos financeiros.

Valores monetários devem utilizar Decimal no Python e NUMERIC no banco de dados, evitando erros de arredondamento.

As operações financeiras que alteram múltiplos registros deverão utilizar transações no banco.

## 20. Modelagem do banco de dados

Criar inicialmente tabelas para:

- usuarios
- grupos_familiares
- integrantes_grupo
- contas_bancarias
- categorias
- subcategorias
- receitas
- despesas
- divisao_despesas
- transferencias
- cartoes_credito
- compras_cartao
- parcelas_cartao
- faturas
- pagamentos_fatura
- recorrencias
- orcamentos
- metas_financeiras
- contribuicoes_metas
- dividas
- parcelas_dividas
- notificacoes
- anexos
- auditoria

Definir corretamente as relações entre as entidades.

Evitar duplicidade de movimentações e garantir consistência dos saldos.

## 21. Regras financeiras importantes

1. Uma despesa paga não deve ser contabilizada duas vezes.
2. Compras no crédito devem impactar a fatura correta.
3. O pagamento de uma fatura não deve criar uma nova despesa de consumo.
4. Transferências entre contas não representam renda.
5. Despesas compartilhadas devem entrar apenas uma vez no total consolidado do casal.
6. Cada integrante deverá possuir seus próprios indicadores.
7. Lançamentos pendentes e realizados devem ser identificados separadamente.
8. Receitas previstas não podem ser confundidas com dinheiro já recebido.
9. Saldos bancários devem considerar as movimentações efetivamente liquidadas.
10. Parcelamentos devem ser gerados respeitando a quantidade de parcelas e o calendário do cartão.
11. Exclusões de registros financeiros devem exigir confirmação e preservar histórico de auditoria quando necessário.
12. Cálculos e regras financeiras devem ser executados no backend, não depender apenas do JavaScript.

## 22. Desenvolvimento em etapas

Não desenvolver tudo de uma única vez.

### Etapa 1 — MVP funcional
- Criar a estrutura do projeto.
- Configurar FastAPI.
- Criar banco de dados.
- Implementar cadastro e login.
- Criar grupo familiar.
- Implementar cadastro de contas.
- Implementar receitas e despesas.
- Criar categorias.
- Criar dashboard básico.
- Implementar divisão de despesas.

### Etapa 2 — Gestão financeira
- Cartões de crédito.
- Compras parceladas.
- Contas recorrentes.
- Orçamento mensal.
- Calendário financeiro.
- Contas a pagar.

### Etapa 3 — Planejamento
- Metas financeiras.
- Gestão de dívidas.
- Projeções.
- Alertas.
- Relatórios avançados.

### Etapa 4 — Evolução
- Importação de extratos CSV/OFX.
- Conciliação financeira.
- Exportação Excel e PDF.
- Melhorias para dispositivos móveis.
- Backup e restauração.
- Implantação em servidor.
- Integrações bancárias futuras, quando disponíveis e autorizadas.

## 23. Desenvolvimento didático

Durante todo o desenvolvimento, atue também como professor de programação.

Para cada funcionalidade:

1. Explique o problema que será resolvido.
2. Apresente os conceitos técnicos utilizados.
3. Mostre os arquivos que serão criados.
4. Explique o objetivo de cada arquivo.
5. Apresente o código completo.
6. Explique os principais trechos, linha por linha quando necessário.
7. Explique como o frontend se comunica com a API.
8. Explique como os dados são armazenados.
9. Demonstre como testar a funcionalidade.
10. Apresente exercícios para reforçar o aprendizado.

Não avance sem entregar uma etapa funcional e testável.

Utilize linguagem didática e exemplos relacionados ao controle financeiro do casal.

**Instrução final:** comece apresentando a arquitetura completa do Rita & Jean Finance, a estrutura das pastas, o modelo inicial do banco de dados e o planejamento do MVP. Em seguida, implemente o primeiro módulo utilizando Python, FastAPI, SQLite, HTML, CSS e JavaScript puro.
