from flask import Blueprint
from flask import flash
from flask import render_template
from flask import request

from .auth import login_required

bp = Blueprint("calculos", __name__)

FAIXAS_IRPF = [
    (2428.80, 0.0, 0.0),
    (2826.65, 0.075, 182.16),
    (3751.05, 0.15, 394.16),
    (4664.68, 0.225, 675.49),
    (float("inf"), 0.275, 908.73),
]

DESCONTO_SIMPLIFICADO = 607.20
REDUCAO_MAXIMA = 312.89
LIMITE_ISENCAO = 5000.00
LIMITE_REDUCAO = 7350.00


def calcular_irpf(salario_bruto):
    base = max(salario_bruto - DESCONTO_SIMPLIFICADO, 0)

    aliquota = 0.0
    imposto_tabela = 0.0
    for limite, aliq, deducao in FAIXAS_IRPF:
        if base <= limite:
            aliquota = aliq
            imposto_tabela = max(base * aliq - deducao, 0)
            break

    if salario_bruto <= LIMITE_ISENCAO:
        reducao = min(REDUCAO_MAXIMA, imposto_tabela)
    elif salario_bruto <= LIMITE_REDUCAO:
        reducao = max(978.62 - 0.133145 * salario_bruto, 0)
        reducao = min(reducao, imposto_tabela)
    else:
        reducao = 0.0

    return {
        "base": round(base, 2),
        "aliquota": round(aliquota * 100, 1),
        "imposto_tabela": round(imposto_tabela, 2),
        "reducao": round(reducao, 2),
        "desconto": round(max(imposto_tabela - reducao, 0), 2),
    }


def calcular_rescisao(salario_base, meses_trabalhados):
    """Recebe o salário base e os meses trabalhados e retorna o valor
    proporcional aproximado do 13º salário (salário / 12 * meses)."""
    return {
        "avos": meses_trabalhados,
        "decimo_terceiro": round(salario_base / 12 * meses_trabalhados, 2),
    }


def _ler_salario(campo):
    """Converte o campo do formulário em salário positivo (aceita vírgula)."""
    valor = float(request.form[campo].replace(",", "."))
    if valor <= 0:
        raise ValueError("O salário deve ser maior que zero.")
    return valor


@bp.route("/painel", methods=("GET", "POST"))
@login_required
def painel():
    """Painel com as duas ferramentas. Nada é salvo no banco de dados:
    os dados entram pelo formulário, são processados e voltam na resposta."""
    resultado_irpf = None
    resultado_rescisao = None

    if request.method == "POST":
        ferramenta = request.form.get("ferramenta")
        error = None

        try:
            if ferramenta == "irpf":
                salario = _ler_salario("salario_bruto")
                resultado_irpf = calcular_irpf(salario)

            elif ferramenta == "rescisao":
                salario = _ler_salario("salario_base")
                meses = int(request.form["meses"])
                if not 1 <= meses <= 12:
                    raise ValueError("Os meses trabalhados devem estar entre 1 e 12.")
                resultado_rescisao = calcular_rescisao(salario, meses)

            else:
                error = "Ferramenta inválida."

        except (KeyError, ValueError) as exc:
            error = str(exc) if isinstance(exc, ValueError) and exc.args and \
                not exc.args[0].startswith(("could not", "invalid literal")) \
                else "Informe valores numéricos válidos."

        if error is not None:
            flash(error)

    return render_template(
        "calculos/painel.html",
        resultado_irpf=resultado_irpf,
        resultado_rescisao=resultado_rescisao,
    )