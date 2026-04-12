def calcular_saldo(salarios, despesas):
    """Calcula o saldo final com base em listas de valores."""
    return sum(salarios) - sum(despesas)


def validar_valor(valor):
    """Garante que o valor inserido é um número positivo."""
    if not isinstance(valor, (int, float)) or valor < 0:
        raise ValueError("O valor deve ser um número positivo.")
    return True
