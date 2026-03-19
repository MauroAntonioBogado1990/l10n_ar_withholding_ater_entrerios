# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountTax(models.Model):
    _inherit = "account.tax"

    tax_ater_entrerios_ret = fields.Boolean(
        'Imp. Ret ATER Entre Ríos',
        default=False
    )

    def create_payment_withholdings(self, payment_group):
        for rec in self:
            if rec.tax_ater_entrerios_ret:
                return
            else:
                return super(AccountTax, rec).create_payment_withholdings(payment_group)
