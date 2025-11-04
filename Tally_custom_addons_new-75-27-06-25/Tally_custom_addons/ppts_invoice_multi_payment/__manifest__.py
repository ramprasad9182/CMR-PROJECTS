# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Multiple Invoice Payment
#
##############################################################################
{
    'name': 'Multiple Invoice Payment',
    'version': '17.0',
    'sequence': 1,
    'description': """ App will allow multiple invoice payment from payment""",
    "category": 'Accounting',
    'summary': 'These apps use to easy payment multi invoice payment',
    'author': 'Point Perfect Technology Solutions',
    'website': 'https://www.pptssolutions.com',
    'license': 'OPL-1',
    'depends': ['sale_management', 'account'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/account_payment.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
