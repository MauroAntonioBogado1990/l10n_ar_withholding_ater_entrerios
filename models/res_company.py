# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    tax_per_ater_entrerios = fields.Many2one(
        'account.tax',
        'Impuesto de Percepción Entre Ríos (ATER)',
        domain=[
            ('type_tax_use', '=', 'sale'),
            ('tax_group_id.l10n_ar_tribute_afip_code', '=', '07')
        ],
        company_dependent=True
    )
