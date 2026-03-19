# -*- coding: utf-8 -*-
from odoo import models, api, fields
from datetime import date
import logging
_logger = logging.getLogger(__name__)


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    def calculate_perceptions(self):
        """
        Calcula la percepción ATER Entre Ríos sobre el monto neto de IVA.
        Alícuota general: 3%
        Penalidad por no acreditar inscripción: 6%
        """
        if self.move_type in ('out_invoice', 'out_refund'):
            if not self.invoice_date:
                self.invoice_date = date.today()
            if self.invoice_line_ids and self.partner_id:
                # Verificamos que el partner tenga alícuota entreríos activa
                tiene_er = (
                    self.partner_id.alicuota_per_entrerios > 0
                    or self.partner_id.alicuota_per_entrerios_6
                )
                # Si ninguna flag especial, usamos alícuota general 3% solo si
                # el impuesto de percepción Entre Ríos está configurado en la compañía
                imp_per_ater = self.company_id.tax_per_ater_entrerios
                if not imp_per_ater:
                    return super(AccountMoveInherit, self).calculate_perceptions()

                # Obtenemos la alícuota del partner (3% general o 6% penalidad)
                alicuota = self.partner_id.get_amount_alicuot_entrerios('per', self.invoice_date)
                imp_per_ater.amount = alicuota

                for iline in self.invoice_line_ids:
                    _tiene_percepcion = 0
                    for tax in iline.tax_ids:
                        if str(imp_per_ater.id) == str(tax.id)[-2:]:
                            _tiene_percepcion = 1
                    if not _tiene_percepcion and imp_per_ater.amount > 0:
                        iline.write({'tax_ids': [(4, imp_per_ater.id)]})

                # Recomputamos apuntes contables
                for lac in self.line_ids:
                    if lac.account_id.id == self.partner_id.property_account_receivable_id.id:
                        if self.move_type == 'out_invoice':
                            if self.currency_id.name != 'ARS':
                                debit_tmp = sum(l.credit for l in self.line_ids)
                                lac.write({'debit': debit_tmp})
                            else:
                                lac.write({'debit': self.amount_total})
                        elif self.move_type == 'out_refund':
                            if self.currency_id.name != 'ARS':
                                credit_tmp = sum(l.debit for l in self.line_ids)
                                lac.write({'credit': credit_tmp})
                            else:
                                lac.write({'credit': self.amount_total})

        return super(AccountMoveInherit, self).calculate_perceptions()
