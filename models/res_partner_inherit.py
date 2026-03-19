# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Entre Ríos - alícuota general 3%, penalidad 6%
    alicuota_per_entrerios = fields.Float('Ali. Percepciones Entre Ríos')
    alicuota_per_entrerios_6 = fields.Boolean('Ali. Percepciones Entre Ríos 6% (penalidad)')
    alicuota_ret_entrerios = fields.Float('Ali. Retenciones Entre Ríos')
    alicuota_ret_entrerios_6 = fields.Boolean('Ali. Retenciones Entre Ríos 6% (penalidad)')

    def get_amount_alicuot_entrerios(self, type_alicuot, date):
        """
        Retorna la alícuota correspondiente para Entre Ríos según ATER:
        - 3% general (inscriptos en IIBB con jurisdicción en Entre Ríos)
        - 6% penalidad (no acredita condición de inscripto)
        - O el valor personalizado si ninguna opción especial está activa
        """
        amount_alicuot = 0.00
        if type_alicuot == 'per':
            if self.alicuota_per_entrerios_6:
                amount_alicuot = 6.00
            elif self.alicuota_per_entrerios > 0:
                amount_alicuot = self.alicuota_per_entrerios
            else:
                # Alícuota general ATER: 3%
                amount_alicuot = 3.00
        if type_alicuot == 'ret':
            if self.alicuota_ret_entrerios_6:
                amount_alicuot = 6.00
            elif self.alicuota_ret_entrerios > 0:
                amount_alicuot = self.alicuota_ret_entrerios
            else:
                # Alícuota general ATER: 3%
                amount_alicuot = 3.00
        return amount_alicuot
