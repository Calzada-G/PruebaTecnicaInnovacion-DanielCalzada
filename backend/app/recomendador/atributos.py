"""Recomendacion por atributos del producto y perfil de plaza.

Es el motor del sistema, no el historico. Con 42 tickets las reglas de
asociacion solo cubren lo que ya se vendio junto; esta capa cubre lo que
deberia venderse junto, y por eso resuelve los dos arranques en frio:
SKU027 (cero ventas) y Merida (cero historial).

Las tablas de abajo son CONOCIMIENTO DE NEGOCIO DECLARADO. No salen de los
datos: las pondria un jefe de piso. Estan aqui, juntas y comentadas, para que
el negocio pueda discutirlas sin leer el resto del codigo.
"""

import sqlite3

from .base import Candidato
from .perfiles import MOTIVO_PLAZA, VENTAJA_AMBIENTE, adecuacion, ambiente, normalizar

# Familias funcionales: mismo trabajo, distinto material o ambiente. Son la
# base de los sustitutos y nunca son complementos entre si.
#
# En produccion esto seria una columna `familia` en el maestro de productos.
# Como constante es honesto para una POC de 28 SKUs, pero no escala: un alta
# nueva no entra en ninguna familia hasta que alguien la agregue aqui.
FAMILIAS: dict[str, tuple[str, ...]] = {
    "tornilleria_1_4": ("SKU005", "SKU006", "SKU007"),
    "lamina_calibre_24": ("SKU008", "SKU009"),
    "tubo_3_4": ("SKU010", "SKU011"),
    "recubrimiento": ("SKU014", "SKU015", "SKU016"),
    "cable_100m": ("SKU022", "SKU023"),
    "candado": ("SKU024", "SKU025"),
}

# Mejora minima de adecuacion para proponer un cambio. Por debajo de esto el
# sustituto no compensa hacerle perder tiempo al vendedor.
MARGEN_SUSTITUTO = 0.10

# Que tanto se complementan dos roles dentro de la misma actividad.
PARES_ROL: dict[tuple[str, str], float] = {
    ("herramienta_principal", "consumible"): 1.00,
    ("herramienta_principal", "accesorio"): 0.90,
    ("herramienta_principal", "epp"): 0.85,
    ("material", "consumible"): 0.95,
    ("accesorio", "consumible"): 0.70,
    ("accesorio", "herramienta_principal"): 0.65,
    ("consumible", "herramienta_principal"): 0.55,
    ("material", "accesorio"): 0.55,
    ("material", "material"): 0.50,
    ("epp", "epp"): 0.75,
    ("epp", "herramienta_principal"): 0.50,
    ("consumible", "accesorio"): 0.45,
    ("consumible", "consumible"): 0.35,
}

MOTIVO_ROL: dict[tuple[str, str], str] = {
    ("herramienta_principal", "consumible"): "es el consumible que necesita para trabajar",
    ("herramienta_principal", "accesorio"): "completa el equipo",
    ("herramienta_principal", "epp"): "es la proteccion que exige ese trabajo",
    ("material", "consumible"): "es lo que se ocupa para instalarlo",
    ("accesorio", "consumible"): "se gasta en el mismo trabajo",
    ("accesorio", "herramienta_principal"): "es el equipo al que pertenece",
    ("consumible", "herramienta_principal"): "es el equipo que lo usa",
    ("material", "accesorio"): "se ocupa en la misma instalacion",
    ("material", "material"): "se instalan juntos en el mismo trabajo",
    ("epp", "epp"): "se usan en el mismo trabajo",
    ("epp", "herramienta_principal"): "es el trabajo que exige esa proteccion",
    ("consumible", "accesorio"): "se ocupa en el mismo equipo",
    ("consumible", "consumible"): "se gastan en el mismo trabajo",
}

# Actividades que siempre piden proteccion de manos, aunque los guantes no
# pertenezcan a ninguna de ellas.
ACTIVIDADES_CON_EPP_GENERAL = ("soldadura", "perforacion", "estructura")
PESO_EPP_GENERAL = 0.60

# Estructura metalica y recubrimiento se venden juntos cuando comparten
# ambiente: lamina galvanizada con anticorrosiva, no con vinilica de interior.
PESO_ESTRUCTURA_RECUBRIMIENTO = 0.70


def actividad(categoria: str, uso: str, nombre: str) -> str:
    """El trabajo en el que participa el producto.

    El orden de las comprobaciones importa: 'soldadura electrica y electronica'
    contiene 'electric', y clasificarla como actividad electrica desconectaria
    la varilla de estano del soplete.
    """
    texto = normalizar(f"{categoria} {uso} {nombre}")
    if any(p in texto for p in ("soldadura", "soldar", "soplete")):
        return "soldadura"
    if any(p in texto for p in ("perforacion", "broca", "taladro")):
        return "perforacion"
    if any(p in texto for p in ("plomeria", "tuberia", "junta")):
        return "plomeria"
    if "electric" in texto:
        return "electrico"
    if "pintura" in texto:
        return "recubrimiento"
    if any(p in texto for p in ("fijacion", "material")):
        return "estructura"
    if "seguridad" in texto:
        return "seguridad"
    return "general"


def rol(categoria: str, uso: str, nombre: str) -> str:
    """El papel que juega el producto dentro de su actividad."""
    texto = normalizar(f"{categoria} {uso} {nombre}")
    if normalizar(categoria) == "epp":
        return "epp"
    # Un regulador y una manguera se venden como herramienta o consumible, pero
    # frente al soplete los dos son accesorios del mismo equipo.
    if any(p in texto for p in ("repuesto", "regulador", "control de presion")):
        return "accesorio"
    if "herramienta" in normalizar(categoria):
        return "herramienta_principal"
    if normalizar(categoria) == "consumible":
        return "consumible"
    return "material"


def familia(sku: str) -> str | None:
    for nombre_familia, miembros in FAMILIAS.items():
        if sku in miembros:
            return nombre_familia
    return None


class AtributosStrategy:
    """Genera sustitutos por familia+ambiente y complementos por rol+actividad."""

    nombre = "atributos"

    def __init__(self, bd: sqlite3.Connection):
        self._productos = {
            f["sku"]: dict(f)
            for f in bd.execute(
                """SELECT sku, nombre, categoria, material, uso_recomendado
                     FROM productos"""
            ).fetchall()
        }
        self._perfiles = {
            f["id"]: f["perfil"] for f in bd.execute("SELECT id, perfil FROM tiendas")
        }
        self._rasgos = {
            sku: (
                actividad(p["categoria"], p["uso_recomendado"], p["nombre"]),
                rol(p["categoria"], p["uso_recomendado"], p["nombre"]),
                ambiente(p["uso_recomendado"], p["material"]),
            )
            for sku, p in self._productos.items()
        }

    def generar(self, sku: str, tienda: str) -> list[Candidato]:
        if sku not in self._productos:
            return []
        perfil = self._perfiles.get(tienda, "interior_urbano")
        return self._sustitutos(sku, perfil) + self._complementos(sku)

    def _sustitutos(self, sku: str, perfil: str) -> list[Candidato]:
        nombre_familia = familia(sku)
        if nombre_familia is None:
            return []

        _, _, amb_ancla = self._rasgos[sku]
        adecuacion_ancla = adecuacion(perfil, amb_ancla)

        candidatos = []
        for otro in FAMILIAS[nombre_familia]:
            if otro == sku or otro not in self._productos:
                continue
            _, _, amb_otro = self._rasgos[otro]
            mejora = adecuacion(perfil, amb_otro) - adecuacion_ancla
            # Solo se propone cambiar si la plaza gana algo. Si el ancla ya es
            # el material correcto para esta tienda, no hay sustituto.
            if mejora < MARGEN_SUSTITUTO:
                continue
            candidatos.append(
                Candidato(
                    sku=otro,
                    tipo="sustituto",
                    score=adecuacion(perfil, amb_otro),
                    fuente=self.nombre,
                    justificacion=(
                        f"{self._productos[otro]['material']}: "
                        f"{VENTAJA_AMBIENTE[amb_otro]}, "
                        f"{MOTIVO_PLAZA.get(perfil, '')}."
                    ),
                )
            )
        return candidatos

    def _complementos(self, sku: str) -> list[Candidato]:
        act_ancla, rol_ancla, amb_ancla = self._rasgos[sku]
        familia_ancla = familia(sku)
        candidatos = []

        for otro, (act_otro, rol_otro, amb_otro) in self._rasgos.items():
            if otro == sku:
                continue
            # Misma familia es sustituto, jamas complemento: nadie se lleva el
            # tornillo de carbon y el de inoxidable para el mismo trabajo.
            if familia_ancla is not None and familia(otro) == familia_ancla:
                continue

            peso, motivo = self._regla(
                act_ancla, rol_ancla, amb_ancla, act_otro, rol_otro, amb_otro
            )
            if peso <= 0:
                continue
            candidatos.append(
                Candidato(
                    sku=otro,
                    tipo="complemento",
                    score=peso,
                    fuente=self.nombre,
                    justificacion=f"Para {act_ancla}: {motivo}.",
                )
            )
        return candidatos

    def _regla(
        self,
        act_ancla: str,
        rol_ancla: str,
        amb_ancla: str,
        act_otro: str,
        rol_otro: str,
        amb_otro: str,
    ) -> tuple[float, str]:
        if act_ancla == act_otro:
            par = (rol_ancla, rol_otro)
            if par in PARES_ROL:
                return PARES_ROL[par], MOTIVO_ROL[par]
            return 0.0, ""

        if (
            rol_otro == "epp"
            and act_otro == "general"
            and act_ancla in ACTIVIDADES_CON_EPP_GENERAL
        ):
            return PESO_EPP_GENERAL, "es la proteccion basica para ese trabajo"

        if (
            act_ancla == "estructura"
            and act_otro == "recubrimiento"
            and amb_otro == amb_ancla
        ):
            return (
                PESO_ESTRUCTURA_RECUBRIMIENTO,
                "es el recubrimiento que le corresponde a ese ambiente",
            )

        return 0.0, ""
