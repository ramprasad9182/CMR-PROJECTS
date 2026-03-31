{
    'name': 'Tally Live Dashboard',
    'Version': '1.0',
    'category': 'Tally Dashboard HO to Stores',
    'author': 'New Horizons CyberSoft Ltd',
    'company': 'New Horizons CyberSoft Ltd',
    'maintainer': 'New Horizons CyberSoft Ltd',
    'website': "https://www.nhclindia.com",
    'depends': ['integration_admin_panel','odoo_tally_integration','base'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/tally_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tally_dashboard/static/src/js/tally_dashboard.js',
            'tally_dashboard/static/src/xml/tally_dashboard.xml',
        ],
    },
    'licence': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
