# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Retenciones y Percepciones ATER Entre Ríos',
    'version': '18.0.1.0.0',
    'summary': 'Retenciones y Percepciones de IIBB para la provincia de Entre Ríos (ATER)',
    'description': """
        Módulo para la gestión de retenciones y percepciones de Ingresos Brutos
        para la provincia de Entre Ríos según normativa ATER.
        
        - Alícuota general: 3% sobre monto neto de IVA
        - Penalidad por no acreditar inscripción: 6%
        - Sujetos pasivos: inscriptos en IIBB con jurisdicción en Entre Ríos
          (contribuyentes directos y Convenio Multilateral)
    """,
    'author': 'Mauro Bogado, Exemax',
    'category': 'Accounting/Localizations',
    'depends': [
        'account',
        'l10n_ar',
        #'l10n_ar_partner',
        'contacts',
        'sale_management',
        #'l10n_ar_withholding_automatic',
        #'l10n_ar_withholding',
    ],
    'data': [
        'security/ir.model.access.csv',
        #'views/account_tax_inherit_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'views/account_export_ater_entrerios_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
