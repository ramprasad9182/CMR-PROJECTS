# -*- coding: utf-8 -*-
{
    'name': "Invoice to Stock Picking",
    'version': '16.0',
    'summary': """Stock Picking From Customer/Vendor Invoice""",
    'description': """This Module Enables to Create Stock Picking From Customer/Vendor Invoice""",
    'author': "PPTS [India] Pvt.Ltd.",
    'website': "https://www.pptssolutions.com",
    'category': 'Accounting',
    'depends': ['base', 'account', 'stock', 'sale'],
    'data': [
        # 'views/account_move_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
