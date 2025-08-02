{
    'name': 'ODOO_TALLY',
    'description': """
This module contains all the common features of Transport and Masters
    """,
    'depends': ['base','account','l10n_in','analytic',],
    'data': [
        # 'security/groups.xml',
        # 'data/public_user_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/account_group_view.xml',
        'views/state_company_master_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}