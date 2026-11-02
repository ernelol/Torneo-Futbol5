"""Validaciones de campos en el back-end (2da capa; la 1ra es HTML y la 3ra la base de datos).

Cada función recibe el texto que llegó del formulario y devuelve el valor ya
convertido, o lanza ReglaError con un mensaje claro.
"""
import re
from datetime import date

from db import ReglaError

REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def texto(valor, campo, maximo=80):
    valor = (valor or "").strip()
    if not valor:
        raise ReglaError(f"{campo}: es obligatorio.")
    if len(valor) > maximo:
        raise ReglaError(f"{campo}: máximo {maximo} caracteres.")
    return valor


def email(valor, campo="Email"):
    valor = texto(valor, campo, 100)
    if not REGEX_EMAIL.match(valor):
        raise ReglaError(f"{campo}: formato inválido.")
    return valor


def entero(valor, campo, minimo, maximo):
    try:
        numero = int((valor or "").strip())
    except ValueError:
        raise ReglaError(f"{campo}: debe ser un número entero.")
    if not minimo <= numero <= maximo:
        raise ReglaError(f"{campo}: debe estar entre {minimo} y {maximo}.")
    return numero


def ci(valor):
    """Cédula sin puntos ni guión, de 6 a 8 dígitos."""
    valor = (valor or "").strip()
    if not re.fullmatch(r"\d{6,8}", valor):
        raise ReglaError("Cédula: ingresá de 6 a 8 dígitos, sin puntos ni guión.")
    return int(valor)


def fecha(valor, campo):
    try:
        return date.fromisoformat((valor or "").strip())
    except ValueError:
        raise ReglaError(f"{campo}: fecha inválida.")


def opcion(valor, campo, permitidas):
    if valor not in permitidas:
        raise ReglaError(f"{campo}: valor no permitido.")
    return valor
