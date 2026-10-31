"""Numeración persistente: un contador bloqueado por modelo y base de datos."""
import re
import uuid
from django.db import transaction,router

def siguiente(modelo,campo,prefijo,ancho=3,minimo=0,using=None):
    from cuentas.models import SecuenciaCodigo
    using=using or router.db_for_write(modelo)
    clave=f'{modelo._meta.label_lower}.{campo}.{prefijo}'
    with transaction.atomic(using=using):
        fila,_=SecuenciaCodigo.objects.using(using).get_or_create(clave=clave)
        fila=SecuenciaCodigo.objects.using(using).select_for_update().get(pk=fila.pk)
        patron=re.compile(rf'^{re.escape(prefijo)}(\d+)$')
        maximo=max(fila.ultimo,minimo)
        for valor in modelo.objects.using(using).values_list(campo,flat=True):
            match=patron.fullmatch(str(valor or ''))
            if match:
                maximo=max(maximo,int(match.group(1)))
        fila.ultimo=maximo+1
        fila.save(using=using,update_fields=['ultimo'])
        return f'{prefijo}{fila.ultimo:0{ancho}d}'

class CodigoAutomaticoMixin:
    def save(self,*args,**kwargs):
        using=kwargs.get('using') or router.db_for_write(type(self),instance=self)
        if not self._state.adding:
            original=type(self).objects.using(using).filter(pk=self.pk).values_list('codigo',flat=True).first()
            if original:
                self.codigo=original
        if not getattr(self,'codigo',None):
            self.codigo=siguiente(type(self),'codigo',self.prefijo_codigo,using=using)
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields']=set(kwargs['update_fields'])|{'codigo'}
        if self._meta.model_name=='actividad' and not self.codigo_verificador:
            self.codigo_verificador='VER-'+uuid.uuid4().hex
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields']=set(kwargs['update_fields'])|{'codigo_verificador'}
        return super().save(*args,**kwargs)
