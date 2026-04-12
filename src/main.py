from financas import calcular_saldo, validar_valor


def menu():
    salarios = []
    despesas = []
    print("--- Gerenciador Financeiro CLI ---")

    while True:
        try:
            prompt = "Digite um salário (ou 0 para calcular): "
            val = float(input(prompt))
            if val == 0:
                break
            if validar_valor(val):
                salarios.append(val)
        except ValueError as e:
            print(f"Erro: {e}")

    saldo = calcular_saldo(salarios, despesas)
    print(f"\nSeu saldo final é: R$ {saldo:.2f}")


if __name__ == "__main__":
    menu()
    