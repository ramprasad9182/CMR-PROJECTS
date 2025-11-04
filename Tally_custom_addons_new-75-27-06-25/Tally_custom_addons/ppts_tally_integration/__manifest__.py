# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': ' Tally Integration v16',
    'version': '1.0.0',
    'category': 'Company',
    'summary': 'This module integrate Odoo to Tally and tally to odoo',
    'description': """
                This module integrate Odoo to Tally and tally to odoo.    """,
    # "author": "PPTS [India] Pvt.Ltd.",
    # 'website': 'www.pptssolutions.com',
    'depends': ["web", "bus", 'base', 'account', 'sale', 'stock',
                'ppts_invoice_stock_update', 'ppts_invoice_multi_payment'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/ppts_tally_integration_views.xml',
        'views/ppts_tally_database_conf_view.xml',
        'views/am_account_group.xml',
        'views/am_account_account_views.xml',
        'views/am_account_move_views.xml',
        'views/res_partner_view.xml',
        # 'views/im_stock_inventory.xml',
        'views/res_users.xml',
        # 'views/purchase_transaction_views.xml',
        'views/ppts_tally_fields_views.xml',
        # 'views/sale_transaction_views.xml',
        # 'views/receipt_note_view.xml'
    ],
    "assets": {
        "web.assets_backend": [
            # "ppts_tally_integration/static/src/js/services/*.js",
        ]
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
}
