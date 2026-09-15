Estas regras são a fonte da verdade para os testes automatizados da seção 12. Sempre que uma regra
abaixo mudar, os testes correspondentes devem ser atualizados no mesmo Pull Request.
Multi-tenancy / Isolamento de dados
•​ Toda query de leitura deve ser filtrada por company=request.user.company — nunca confiar
apenas no ID da URL.
•​ Nenhum endpoint pode retornar ou aceitar um ID pertencente a outra empresa (validar no
serializer/view, não só no template).
•​ Recomenda-se criar um QuerySet/Manager customizado (ex.: CompanyManager) que já filtra por
empresa, para tornar o isolamento o comportamento padrão e não uma checagem manual
espalhada pelo código.
•​ Superusuário de plataforma (staff da Anthropic... digo, do GestorX) é a única exceção
documentada, com acesso via painel administrativo separado.
Vendas (Sale)
•​ Uma venda deve ter ao menos 1 SaleItem para ser confirmada.
•​ quantity de cada item deve ser > 0.
•​ Não é permitido vender produto inativo.
•​ Não é permitido vender quantidade maior que o estoque disponível (validação antes de confirmar).
•​ unit_price do item é congelado no momento da venda (não usar product.price em relatórios
futuros).
•​ subtotal = soma de (unit_price * quantity - discount) de cada item.
•​ total = subtotal - discount da venda.
•​ Confirmar a venda deve ser atômico: criar SaleItems, dar baixa no estoque (via StockMovement) e
opcionalmente gerar Receivable, tudo dentro de uma única transaction.atomic(). Se qualquer etapa
falhar, nada é persistido.
•​ Cancelar uma venda deve devolver o estoque (StockMovement do tipo 'in' com motivo
'Cancelamento venda #X') e marcar status=cancelled com cancel_reason obrigatório.
•​ Apenas usuários com permissão sales.cancel podem cancelar vendas.
Estoque (Stock)
•​ O saldo de estoque nunca deve ser alterado diretamente (product.stock -= x). Toda alteração passa
por um StockMovement, e o saldo é recalculado ou atualizado dentro do mesmo
service/transaction que cria o movimento.
•​ Toda venda confirmada gera StockMovement(type='out') por item vendido.
•​ Todo cancelamento de venda gera StockMovement(type='in') de estorno.
•​ Ajustes manuais de estoque exigem motivo (reason) preenchido e usuário com permissão
adequada.•​ Quando stock <= minimum_stock, o sistema deve gerar uma Notification de estoque baixo (pode
ser síncrono no MVP, assíncrono via Celery depois).
Financeiro (Receivable / Payable)
•​ Status válido: pending → paid ou pending → cancelled. overdue é derivado automaticamente
(due_date < hoje e status ainda pending) — pode ser calculado em query/property, não precisa ser
um campo gravado manualmente.
•​ Uma Receivable pode nascer automaticamente de uma Sale (quando a venda for 'a prazo').
•​ Marcar como pago exige payment_method e preenche paid_at.
•​ Somatórios do dashboard financeiro (a receber, a pagar, recebido, pago) devem ser calculados via
agregação no banco (Sum, annotate), nunca em loop Python.
Permissões
•​ Toda view/endpoint deve checar permissão explicitamente — nunca assumir que 'estar logado' é
suficiente.
•​ Regra por papel (role) cobre o MVP; permissões granulares (ex.: sales.cancel) chegam no Nível 3,
via django-guardian, grupos do Django ou solução própria.
•​ Um usuário nunca pode alterar seu próprio role para elevar privilégio.
•​ Testar explicitamente: usuário sem permissão não pode acessar/alterar recurso, mesmo sabendo o
ID correto.
Auditoria
•​ Ações sensíveis (alterar preço, cancelar venda, excluir cliente, alterar permissão de usuário) devem
gerar AuditLog.
•​ AuditLog é append-only: não existe endpoint de update/delete para ele.
•​ changes deve registrar valores antes/depois em formato estruturado (JSON), não apenas texto
livre.
SaaS / Planos
•​ Limites do plano (max_users, max_clients, max_products) devem ser verificados antes de criar o
registro, não depois.
•​ Ao atingir o limite, a criação deve falhar com mensagem clara indicando a necessidade de upgrade
— nunca falhar silenciosamente.
•​ Mudança de plano (upgrade/downgrade) deve ser registrada com data de vigência; downgrade não
pode quebrar dados já existentes acima do novo limite (ex.: empresa com 15 usuários que faz
downgrade para plano de 10 — os 15 continuam existindo, mas não é possível criar novos até ficar
dentro do limite).
