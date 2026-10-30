from datetime import date

from src.folego.apresentacao.gasto import ler_formulario
from src.folego.modelos import CATEGORIAS_PADRAO, Gasto

HOJE = date(2026, 10, 5)


def test_ler_formulario_valor_e_categoria():
    g = ler_formulario("1.500,00", "03/10/2026", " Mercado ", "Outros", HOJE, CATEGORIAS_PADRAO)
    assert g == Gasto(150_000, date(2026, 10, 3), "Mercado", 5)
    assert ler_formulario("150,5", "", "", "Outros", HOJE, CATEGORIAS_PADRAO).valor_centavos == 15_050
    assert isinstance(ler_formulario("abc", "", "", "Outros", HOJE, CATEGORIAS_PADRAO), str)
    assert isinstance(ler_formulario("10", "", "", "Inexistente", HOJE, CATEGORIAS_PADRAO), str)


def test_ler_formulario_data_dd_mm_e_ilegivel():
    assert ler_formulario("10", "03/10", "", "Outros", HOJE, CATEGORIAS_PADRAO).data == date(2026, 10, 3)
    assert ler_formulario("10", "", "", "Outros", HOJE, CATEGORIAS_PADRAO).data == HOJE
    for ruim in ("31/02", "ontem", "1/2/3/4", "10-10-2026"):
        assert isinstance(ler_formulario("10", ruim, "", "Outros", HOJE, CATEGORIAS_PADRAO), str)
