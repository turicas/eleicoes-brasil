from .modelo import Resultado


def escolher_cobertura(nacional: Resultado | None, soma: Resultado | None) -> Resultado:
    """Prefere o nacional em empate; compara cobertura, nunca timestamps ou percentuais arredondados."""
    if nacional is None and soma is None:
        raise ValueError("Nenhuma fonte presidencial disponível")
    if nacional is None:
        return soma
    if soma is None:
        return nacional
    if nacional.contexto != soma.contexto:
        raise ValueError("Contextos presidenciais incompatíveis")
    if nacional.secoes.total != soma.secoes.total:
        raise ValueError("Total geral de seções incompatível entre nacional e soma")
    if soma.secoes.totalizadas is None:
        return nacional
    if nacional.secoes.totalizadas is None:
        return soma
    return soma if soma.secoes.totalizadas > nacional.secoes.totalizadas else nacional
