# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class AccountExportAterEntrerios(models.Model):
    _name = 'account.export.ater.entrerios'
    _description = 'Exportación ATER Entre Ríos - Retenciones y Percepciones IIBB'

    name = fields.Char('Nombre')
    date_from = fields.Date('Fecha desde')
    date_to = fields.Date('Fecha hasta')

    export_ater_data_ret = fields.Text(
        'Contenido archivo ATER Entre Ríos Retenciones', default=''
    )
    export_ater_data_per = fields.Text(
        'Contenido archivo ATER Entre Ríos Percepciones', default=''
    )

    tax_withholding = fields.Many2one(
        'account.tax',
        'Imp. de Ret utilizado',
        domain=[('tax_ater_entrerios_ret', '=', True)],
        required=True
    )

    # --- Retenciones ---
    @api.depends('export_ater_data_ret')
    def _compute_files_ret(self):
        self.ensure_one()
        self.export_ater_filename_ret = _('ATER_entrerios_ret_%s_%s.txt') % (
            str(self.date_from), str(self.date_to)
        )
        self.export_ater_file_ret = encodebytes(
            self.export_ater_data_ret.encode('ISO-8859-1')
        )

    export_ater_file_ret = fields.Binary(
        'TXT ATER Entre Ríos Ret', compute=_compute_files_ret
    )
    export_ater_filename_ret = fields.Char(
        'Nombre TXT Ret', compute=_compute_files_ret
    )

    # --- Percepciones ---
    @api.depends('export_ater_data_per')
    def _compute_files_per(self):
        self.ensure_one()
        self.export_ater_filename_per = _('ATER_entrerios_per_%s_%s.txt') % (
            str(self.date_from), str(self.date_to)
        )
        self.export_ater_file_per = encodebytes(
            self.export_ater_data_per.encode('ISO-8859-1')
        )

    export_ater_file_per = fields.Binary(
        'TXT ATER Entre Ríos Per', compute=_compute_files_per
    )
    export_ater_filename_per = fields.Char(
        'Nombre TXT Per', compute=_compute_files_per
    )

    def compute_ater_entrerios_data(self):
        self.ensure_one()
        windows_line_ending = '\r\n'

        # =====================================================================
        # RETENCIONES
        # Base imponible: monto neto de IVA (amount_untaxed)
        # Alícuota: 3% general / 6% penalidad
        # =====================================================================
        payments = self.env['account.payment'].search([
            ('payment_type', '=', 'outbound'),
            ('state', 'not in', ['cancel', 'draft']),
            ('date', '<=', self.date_to),
            ('date', '>=', self.date_from),
        ])

        string_ret = ''
        for payment in payments:
            if not payment.withholding_number:
                continue
            if payment.tax_withholding_id.id != self.tax_withholding.id:
                continue
            if not payment.partner_id:
                raise ValidationError(
                    'El pago %s no tiene asignado un proveedor.' % payment.name
                )

            _alicuota_ret = payment.partner_id.get_amount_alicuot_entrerios('ret', self.date_from)

            # Campo 1: Fecha de Retención (dd-mm-aaaa)
            string_ret += (
                str(payment.date)[8:10] + '-'
                + str(payment.date)[5:7] + '-'
                + str(payment.date)[:4] + ','
            )
            # Campo 2: Tipo de Comprobante
            string_ret += 'CR,'
            # Campo 3: Número de Comprobante (12 dígitos)
            string_ret += payment.withholding_number.zfill(12) + ','
            # Campo 4: Razón social
            string_ret += payment.partner_id.name + ','
            # Campo 5: CUIT
            string_ret += str(payment.partner_id.vat) + ','
            # Campo 6: Monto sujeto a retención (neto de IVA)
            string_ret += '%.2f' % payment.withholding_base_amount + ','
            # Campo 7: Alícuota
            string_ret += '%.2f' % _alicuota_ret
            # Campos 8-11: vacíos (sin comprobante de anulación)
            string_ret += ',,,,'
            string_ret += windows_line_ending

        self.export_ater_data_ret = string_ret

        # =====================================================================
        # PERCEPCIONES
        # Base imponible: monto neto de IVA de la factura
        # Alícuota: 3% general / 6% penalidad
        # =====================================================================
        invoices = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '<=', self.date_to),
            ('invoice_date', '>=', self.date_from),
        ], order='invoice_date asc')

        string_per = ''
        for invoice in invoices:
            # Buscamos líneas contables correspondientes a percepción ATER Entre Ríos
            er_lines = invoice.line_ids.filtered(
                lambda l: l.tax_group_id
                and ('Entre' in (l.tax_group_id.name or '') or 'Ríos' in (l.tax_group_id.name or '') or 'Rios' in (l.tax_group_id.name or '') or 'ATER' in (l.tax_group_id.name or ''))
            )

            if not er_lines:
                continue

            for line in er_lines:
                # Monto de la percepción
                if invoice.l10n_latam_document_type_id.internal_type == 'credit_note':
                    tax_group_amount = line.debit
                else:
                    tax_group_amount = line.credit

                # Monto base: líneas de producto (sin tax_group_id) que tengan el impuesto ATER
                base_lines = invoice.line_ids.filtered(
                    lambda l: l.tax_ids and any(
                        t.tax_group_id and (
                            'Entre' in (t.tax_group_id.name or '')
                            or 'Ríos' in (t.tax_group_id.name or '')
                            or 'Rios' in (t.tax_group_id.name or '')
                            or 'ATER' in (t.tax_group_id.name or '')
                        )
                        for t in l.tax_ids
                    ) and not l.tax_group_id
                )
                if invoice.currency_id.name != 'ARS':
                    base_amount = sum(
                        abs(l.balance) * invoice.invoice_currency_rate for l in base_lines
                    )
                else:
                    base_amount = sum(abs(l.balance) for l in base_lines)

                if not invoice.l10n_latam_document_type_id:
                    raise ValidationError(
                        'La factura %s no tiene tipo de documento.' % invoice.name
                    )

                doc_prefix = invoice.l10n_latam_document_type_id.doc_code_prefix.replace('-', '_')

                # Campo 1: Fecha de Percepción (dd/mm/aaaa)
                string_per += (
                    str(invoice.invoice_date)[8:10] + '/'
                    + str(invoice.invoice_date)[5:7] + '/'
                    + str(invoice.invoice_date)[:4] + ','
                )
                # Campo 2: Tipo de Comprobante
                string_per += doc_prefix + ','
                # Campo 3: Número de Comprobante
                string_per += str(invoice.name)[-13:-9] + str(invoice.name)[-8:] + ','
                # Campo 4: Razón social
                string_per += invoice.partner_id.name + ','
                # Campo 5: CUIT (formato 99-99999999-9)
                cuit = invoice.partner_id.vat
                string_per += '{}-{}-{}'.format(cuit[:2], cuit[2:10], cuit[10:])
                # Campo 6: Monto base (neto de IVA)
                string_per += ',' + '%.2f' % base_amount + ','
                # Campo 7: Alícuota
                _alicuota_per = invoice.partner_id.get_amount_alicuot_entrerios('per', self.date_from)
                string_per += '%.2f' % _alicuota_per

                # Campos NC o vacíos
                if invoice.l10n_latam_document_type_id.internal_type == 'credit_note':
                    if not invoice.reversed_entry_id:
                        raise ValidationError(
                            'La NC %s no tiene factura de reversión asociada.' % invoice.name
                        )
                    rev = invoice.reversed_entry_id
                    rev_prefix = rev.l10n_latam_document_type_id.doc_code_prefix.replace('-', '_')
                    string_per += ',' + rev_prefix + ','
                    string_per += str(rev.name)[-13:-9] + str(rev.name)[-8:] + ','
                    string_per += (
                        str(rev.invoice_date)[8:10] + '/'
                        + str(rev.invoice_date)[5:7] + '/'
                        + str(rev.invoice_date)[:4] + ','
                    )
                    cuit_rev = rev.partner_id.vat
                    string_per += '{}-{}-{}'.format(cuit_rev[:2], cuit_rev[2:10], cuit_rev[10:])
                else:
                    string_per += ',,,,'

                string_per += windows_line_ending

        self.export_ater_data_per = string_per
