"""Contrato de los ajustes del negocio sobre las sugerencias.

Vivia dentro de routers/relaciones.py, que era la unica ruta del proyecto que
declaraba sus modelos en linea. Aqui ademas se acotan los pesos: sin cota, un
peso negativo pasaba la validacion y reventaba contra el CHECK de la base con
un 500, cuando es un dato invalido y merece un 422.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

# El nombre de una fuente es el mismo que devuelve `Candidato.fuente`:
# 'historico', 'atributos', 'manual'. Se acota para que un dedazo no cree una
# fila de configuracion nueva que nadie va a leer nunca.
NombreFuente = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, pattern=r"^[a-z][a-z_]{2,29}$"
    ),
]

# 0 apaga la fuente; 1 es su peso natural. El tope no es un limite tecnico sino
# de sentido: por encima de 10 una fuente aplasta a la otra y el hibrido deja
# de serlo, que es justo lo que el panel intenta dejar ajustar con criterio.
Peso = Annotated[float, Field(ge=0, le=10)]


class AjusteRelacion(BaseModel):
    """PATCH: solo se aplica lo que venga en el cuerpo."""

    estado: Literal["activa", "bloqueada", "fijada"] | None = None
    # None explicito borra el override y devuelve la relacion a su score calculado.
    peso_manual: Peso | None = None


class PesosFuentes(BaseModel):
    """Peso de cada fuente en la mezcla del recomendador."""

    pesos: dict[NombreFuente, Peso] = Field(min_length=1)

    # Sin ejemplo, Swagger inventa {"additionalProp1": {}} porque el tipo es un
    # mapa abierto. Con el, la documentacion muestra las fuentes reales.
    model_config = {
        "json_schema_extra": {
            "examples": [{"pesos": {"historico": 1.0, "atributos": 0.6}}]
        }
    }
