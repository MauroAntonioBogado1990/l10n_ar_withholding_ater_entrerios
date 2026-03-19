# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
import logging
_logger = logging.getLogger(__name__)


class AccountPaymentGroupInherit(models.Model):
    _inherit = "account.payment.group"

    def compute_withholdings(self):
        res = super(AccountPaymentGroupInherit, self).compute_withholdings()
        for rec in self:
            # Verificamos que el partner tenga configuración de retención ATER Entre Ríos
            tiene_er = (
                rec.partner_id.alicuota_ret_entrerios > 0
                or rec.partner_id.alicuota_ret_entrerios_6
            )

            # Buscamos el impuesto de retención ATER Entre Ríos configurado
            _imp_ret = self.env['account.tax'].search([
                ('type_tax_use', '=', rec.partner_type),
                ('company_id', '=', rec.company_id.id),
                ('withholding_type', '=', 'partner_iibb_padron'),
                ('tax_ater_entrerios_ret', '=', True),
            ], limit=1)

            if not _imp_ret:
                continue

            # Obtenemos la alícuota: 3% general o 6% penalidad
            retencion = rec.partner_id.get_amount_alicuot_entrerios('ret', rec.payment_date)

            if retencion <= 0:
                continue

            # Calculamos la base imponible (monto neto de IVA de las facturas)
            amount_untaxed_total_invs = 0
            for invs in rec.debt_move_line_ids:
                if invs.move_id.currency_id.name != 'ARS':
                    amount_untaxed_total_invs += (
                        invs.move_id.amount_untaxed * invs.move_id.invoice_currency_rate
                    )
                else:
                    amount_untaxed_total_invs += invs.move_id.amount_untaxed

            amount_untaxed_total_invs += rec.withholdable_advanced_amount
            _amount_ret_iibb = amount_untaxed_total_invs * (retencion / 100)

            _payment_method = self.env.ref(
                'l10n_ar_withholding_automatic.account_payment_method_out_withholding'
            )
            _journal = self.env['account.journal'].search([
                ('company_id', '=', rec.company_id.id),
                ('outbound_payment_method_line_ids.payment_method_id', '=', _payment_method.id),
                ('type', 'in', ['cash', 'bank']),
            ], limit=1)

            # Eliminamos retención previa si existe para recrearla
            payment_withholding = self.env['account.payment'].search([
                ('payment_group_id', '=', rec.id),
                ('tax_withholding_id', '=', _imp_ret.id),
            ], limit=1)
            if payment_withholding:
                payment_withholding.unlink()

            rec.payment_ids = [(0, 0, {
                'name': '/',
                'partner_id': rec.partner_id.id,
                'payment_type': 'outbound',
                'journal_id': _journal.id,
                'tax_withholding_id': _imp_ret.id,
                'payment_method_description': 'Retención IIBB ATER Entre Ríos',
                'payment_method_id': _payment_method.id,
                'date': rec.payment_date,
                'destination_account_id': rec.partner_id.property_account_payable_id.id,
                'amount': _amount_ret_iibb,
                'withholding_base_amount': amount_untaxed_total_invs,
            })]

            # Asignamos la cuenta contable del impuesto al asiento de retención
            line_ret = rec.payment_ids.filtered(
                lambda r: r.tax_withholding_id.id == _imp_ret.id
            )
            line_tax_account = line_ret.move_id.line_ids.filtered(lambda r: r.credit > 0)
            account_imp_ret = _imp_ret.invoice_repartition_line_ids.filtered(
                lambda r: len(r.account_id) > 0
            )
            if account_imp_ret:
                cuenta_anterior = line_ret.move_id.journal_id.default_account_id
                line_ret.move_id.journal_id.default_account_id = account_imp_ret.account_id
                line_tax_account.account_id = account_imp_ret.account_id
                line_ret.move_id.journal_id.default_account_id = cuenta_anterior

        return res
