
"""Serializers para los mantenedores de organizaciones y vecinos."""

from django.core.exceptions import ValidationError
from django.db.models import Q
from rest_framework import serializers

from control_gestion.models import OrganizacionComunitaria
from requerimientos.models import Vecino

from core.validaciones import (
    MENSAJE_RUT,
    rut_normalizado_valido,
    formatear_rut,
)


def validar_rut_opcional(valor):
    """Reutiliza la validacion de RUT existente en el proyecto."""
    if not valor:
        return None

    normalizado = rut_normalizado_valido(valor)

    if normalizado is None:
        raise serializers.ValidationError(MENSAJE_RUT)

    return normalizado


# MANTENEDOR 1: ORGANIZACIONES COMUNITARIAS


class OrganizacionAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganizacionComunitaria
        exclude = (
            "clave_origen",
            "eliminado_en",
        )

    def validate_presidente_rut(self, value):
        return validar_rut_opcional(value)

    def validate_tesorero_rut(self, value):
        return validar_rut_opcional(value)

    def validate_secretario_rut(self, value):
        return validar_rut_opcional(value)


class OrganizacionUsuarioSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganizacionComunitaria
        exclude = (
            "clave_origen",
            "eliminado_en",
            "telefono",
            "correo",
            "presidente_rut",
            "tesorero_rut",
            "secretario_rut",
        )


# MANTENEDOR 2: VECINOS


class VecinoAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vecino
        fields = "__all__"

        extra_kwargs = {
            "rut": {
                "validators": [],
            },
        }

    def validate_rut(self, value):
        normalizado = validar_rut_opcional(value)

        if normalizado is None:
            return None

        vecinos = Vecino.objects.filter(
            Q(rut__iexact=normalizado)
            | Q(rut__iexact=formatear_rut(normalizado))
        )

        if self.instance is not None:
            vecinos = vecinos.exclude(pk=self.instance.pk)

        if vecinos.exists():
            raise serializers.ValidationError(
                "Ya existe un vecino registrado con este RUT."
            )

        return normalizado

    def validate_nombre(self, value):
        vecino = Vecino(nombre=value)

        try:
            vecino.clean()
        except ValidationError as error:
            raise serializers.ValidationError(error.messages)

        if not vecino.nombre:
            raise serializers.ValidationError(
                "El nombre no puede estar vacio."
            )

        return vecino.nombre


class VecinoUsuarioSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vecino
        exclude = (
            "rut",
            "telefono",
            "correo",
        )
