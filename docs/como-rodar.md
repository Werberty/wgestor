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