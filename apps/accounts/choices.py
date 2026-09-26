from django.db import models


class RoleChoice(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    MANAGER = 'manager', 'Manager'
    SELLER = 'seller', 'Seller'
    FINANCE = 'finance', 'Finance'
