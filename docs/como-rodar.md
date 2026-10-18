# Como Rodar

Este projeto é construido com **Django** e **Django REST Framework (DRF)**, utilizando **Docker** para gerenciar tanto a aplicação quanto o banco de dados **PostgreSQL**.

## Requisitos

- Docker
- Docker compose

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/Werberty/wgestor.git
cd wgestor
```
2. Copie o arquivo de exemplo .env e configure suas variáveis:
```bash
cp .env.example .env
```
3. Suba os containers com Docker Compose:
```bash
docker compose up --build -d 
```
4. Acesse o container do Django para rodar migrações:
```bash
docker compose exec web python manage.py migrate
```
5. Crie um superusuário::
```bash
docker compose exec web python manage.py createsuperuser
```

## Testes automatizados

Com os containers em execução, rode a suíte completa:

```bash
docker compose exec web pytest -q
```

Para executar apenas os testes de autenticação e senha:

```bash
docker compose exec web pytest apps/accounts/tests.py -v
```

Os testes usam um banco separado, criado e removido pelo Django. O usuário
do PostgreSQL configurado no `.env` precisa ter permissão para criar bancos.
São cobertos login válido, credenciais inválidas ou ausentes, usuário inativo,
reutilização de token, logout, revogação de acesso e preservação dos tokens
de outros usuários.

Para executar apenas os testes de troca de senha do usuário logado:

```bash
docker compose exec web pytest apps/accounts/tests.py -k password_change -v
```

Esses testes cobrem a troca de senha nos dois prefixos da API, login com a
nova senha, revogação do token anterior, senha atual incorreta, reutilização
da senha, os quatro validadores de senha configurados, campos obrigatórios,
autenticação ausente ou inválida, usuário inativo e métodos HTTP não aceitos.
Também verificam o isolamento entre usuários, a preservação de espaços nas
senhas e o rollback da senha e do token quando a revogação falha.
