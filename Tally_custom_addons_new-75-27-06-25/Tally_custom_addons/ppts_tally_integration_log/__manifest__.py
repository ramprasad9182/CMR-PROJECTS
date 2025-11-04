# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tally Integration Log',
    'version': '1.1.0',
    'category': 'Company',
    'summary': 'This module helps to view Odoo to Tally and tally to odoo sync Log ',
    'description': """This module helps to view Odoo to Tally sync Log""",
    # "author": "PPTS [India] Pvt.Ltd.",
    # 'website': 'www.pptssolutions.com',
    'depends': ['base','ppts_tally_integration'],
    'data': [
        'data/tallyodoo_log_seq.xml',
        'security/ir.model.access.csv',
        'views/ppts_tally_integration_log_views.xml'
    ],
    'demo': [],
    'installable'   : True,
    'application'   : True,
    'auto_install'  : False,
    'license'       : 'LGPL-3',
	# 'images'        : ['static/description/banner.gif'],
}