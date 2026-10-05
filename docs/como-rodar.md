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

Para executar apenas os testes de login e logout:

```bash
docker compose exec web pytest apps/accounts/tests.py -v
```

Os testes usam um banco separado, criado e removido pelo Django. O usuário
do PostgreSQL configurado no `.env` precisa ter permissão para criar bancos.
São cobertos login válido, credenciais inválidas ou ausentes, usuário inativo,
reutilização de token, logout, revogação de acesso e preservação dos tokens
de outros usuários.
