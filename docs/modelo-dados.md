Abaixo estão todas as entidades do MVP até a fase de SaaS/Billing, com campos e relacionamentos.
Tipos são indicativos (Django ORM); ajustem conforme necessidade, mas mudanças de modelagem
devem ser discutidas em dupla antes de implementadas, pois afetam todo o restante do sistema.
Company (Empresa)
Entidade raiz do multi-tenant. Toda entidade relevante do sistema pertence a uma Company.
CampoTipoObservação
idUUID/PKIdentificador único
nameCharField(150)Razão social
trade_nameCharField(150)Nome fantasia
documentCharField(20)CNPJ/CPF, único
emailEmailFieldE-mail de contato
phoneCharField(20)Telefone
planFK → PlanPlano atual (Free/Pro/Enterprise)
is_activeBooleanFieldEmpresa ativa/suspensa
created_at / updated_atDateTimeFieldAuditoria de criação/edição
Relacionamentos: 1:N com User, Client, Product, Sale, StockMovement, Receivable, Payable, Task,
Notification, AuditLog.
User (Usuário)
Usuário customizado do Django (AbstractUser/AbstractBaseUser). Sempre vinculado a uma Company
(exceto superuser de plataforma).
CampoTipo
Observação
idUUID/PKcompanyFK → Company (nullable p/
staff da plataforma)Isolamento multi-tenant
nameCharField(150)Nome completo
emailEmailField (único)Usado como username
roleCharField (choices)admin / manager / seller / finance
is_activeBooleanFieldPermite desativar sem excluir
last_loginDateTimeFieldDjango padrão
created_at / updated_atDateTimeFieldRelacionamentos: N:1 com Company. 1:N com AuditLog (autor das ações), Task (responsável), Sale
(vendedor).
Client (Cliente)
Cliente da empresa (não confundir com 'Company' do SaaS — este é o cliente do cliente).
CampoTipo
Observação
idUUID/PKcompanyFK → CompanynameCharField(150)documentCharField(20)CPF/CNPJ
emailEmailFieldOpcional
phoneCharField(20)Opcional
addressCharField(255) ou FK →
AddressPode iniciar como campo simples
notesTextFieldObservações
is_activeBooleanFieldcreated_at / updated_atDateTimeField
Isolamento
Relacionamentos: N:1 com Company. 1:N com Sale, Receivable.
Category (Categoria de Produto)
Agrupamento de produtos, por empresa.
CampoTipo
idUUID/PK
companyFK → Company
nameCharField(100)
is_activeBooleanField
Observação
Relacionamentos: N:1 com Company. 1:N com Product.
Product (Produto)
Item vendável/estocável da empresa.
CampoTipo
idUUID/PK
companyFK → Company
ObservaçãoCampoTipo
Observação
categoryFK → Category (nullable)nameCharField(150)skuCharField(50)Único por empresa
barcodeCharField(50)Opcional
priceDecimalField(10,2)Preço de venda
costDecimalField(10,2)Custo (para margem)
stockIntegerFieldSaldo atual (calculado/cache)
minimum_stockIntegerFieldGatilho de alerta
is_activeBooleanFieldcreated_at / updated_atDateTimeField
Relacionamentos: N:1 com Company e Category. 1:N com SaleItem, StockMovement.
Sale (Venda)
Cabeçalho da venda. Nunca guarda produto/quantidade diretamente — isso é responsabilidade do
SaleItem.
CampoTipo
Observação
idUUID/PKcompanyFK → CompanyclientFK → ClientsellerFK → UserVendedor responsável
statusCharField (choices)draft / confirmed / cancelled
subtotalDecimalField(10,2)Soma dos itens
discountDecimalField(10,2)Desconto aplicado
totalDecimalField(10,2)subtotal - discount
cancel_reasonTextFieldPreenchido só se cancelada
created_at / updated_atDateTimeField
Relacionamentos: N:1 com Company, Client, User(seller). 1:N com SaleItem. Gera N StockMovement e 1
Receivable (se a prazo).
SaleItem (Item da Venda)
Cada linha de produto dentro de uma venda.CampoTipo
Observação
idUUID/PKsaleFK → SaleproductFK → ProductquantityIntegerField>0
unit_priceDecimalField(10,2)Congelado no momento da venda
discountDecimalField(10,2)Desconto do item
totalDecimalField(10,2)(unit_price * quantity) - discount
Relacionamentos: N:1 com Sale e Product.
StockMovement (Movimentação de Estoque)
Histórico imutável de entradas/saídas — nunca alterar 'product.stock' diretamente no código de negócio.
CampoTipo
Observação
idUUID/PKcompanyFK → CompanyproductFK → ProducttypeCharField (choices)in / out / adjustment
quantityIntegerFieldSempre positivo; o 'type' define o sinal
reasonCharField(255)Ex.: 'Venda #10234', 'Compra', 'Ajuste'
reference_saleFK → Sale (nullable)Rastreabilidade
created_byFK → Usercreated_atDateTimeField
Relacionamentos: N:1 com Company, Product, User, Sale (opcional).
Receivable (Conta a Receber)
Valores a receber de clientes.
CampoTipo
idUUID/PK
companyFK → Company
clientFK → Client
saleFK → Sale (nullable)
amountDecimalField(10,2)
Observação
Se originada de uma vendaCampoTipoObservação
due_dateDateFieldVencimento
statusCharField (choices)pending / overdue / paid / cancelled
payment_methodCharField(30)Opcional
paid_atDateTimeField (nullable)
Relacionamentos: N:1 com Company, Client, Sale (opcional).
Payable (Conta a Pagar)
Despesas/obrigações da empresa.
CampoTipo
Observação
idUUID/PKcompanyFK → Companysupplier_nameCharField(150)amountDecimalField(10,2)due_dateDateFieldstatusCharField (choices)pending / overdue / paid / cancelled
categoryCharField(50)Ex.: aluguel, fornecedor, imposto
Simplificado no MVP (sem cadastro de
Fornecedor)
Relacionamentos: N:1 com Company.
Task (Tarefa)
Módulo interno estilo Kanban.
CampoTipoidUUID/PKcompanyFK → CompanytitleCharField(150)descriptionTextFieldassigneeFK → UserResponsável
priorityCharField (choices)low / medium / high
due_dateDateFieldstatusCharField (choices)
Relacionamentos: N:1 com Company e User.
Observação
pending / in_progress / doneNotification (Notificação)
Avisos gerados pelo sistema (estoque baixo, conta vencendo etc.).
CampoTipo
idUUID/PK
companyFK → Company
userFK → User (nullable)
titleCharField(150)
messageTextField
is_readBooleanField
created_atDateTimeField
Observação
Se null, visível para toda a empresa
Relacionamentos: N:1 com Company e User.
AuditLog (Log de Auditoria)
Registro append-only de ações relevantes (quem fez o quê, quando, valores antes/depois).
CampoTipo
Observação
idUUID/PKcompanyFK → CompanyuserFK → UserAutor da ação
actionCharField(50)created / updated / deleted / cancelled
entityCharField(50)Nome do model afetado
entity_idUUIDchangesJSONFieldcreated_atDateTimeField
{'field': {'old':..., 'new':...}}
Relacionamentos: N:1 com Company e User. Nunca deve ser editado ou apagado pela aplicação.
Plan (Plano) / Subscription (Assinatura)
Introduzido na fase de SaaS/Billing. Plan define limites; Subscription liga Company ao Plan com vigência.
CampoTipo
Plan.idUUID/PK
Plan.nameCharField(50)
Plan.max_usersIntegerField
Plan.max_clientsIntegerField
Observação
Free / Pro / EnterpriseCampoTipo
Plan.max_productsIntegerField
Plan.priceDecimalField(10,2)
Subscription.companyFK → Company
Subscription.planFK → Plan
Subscription.statusCharField (choices)
Subscription.current_peri
od_endDateTimeField
Observação
trialing / active / past_due / cancelled
Relacionamentos: Company 1:1 (ou 1:N histórico) com Subscription; Subscription N:1 com Plan.
