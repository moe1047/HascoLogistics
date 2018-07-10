# -*- coding: utf-8 -*-
{
    'name': "Logistics",

    'summary': """Manage Cargos""",

    'description': """
        Kalkaal's Logistics module is for managing Cargos:
            - Cargo collection
            - Packaging
            - Invoicing
    """,

    'author': "Kalkaal IT Solutions",
    'website': "http://www.kalkaalit.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Logistics',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','report','account','mail','contacts','board'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/kalkaal_logistics.xml',
        'views/invoice.xml',
        'reports/cargo_report.xml',
        'reports/dashboard.xml',
        'wizards/manifest_wizard.xml',
        'reports/manifest.xml',
        'reports/cargo_detail.xml',
        'views/item_type.xml',
        'views/bills.xml',
        'views/config.xml',
        'wizards/cargo_wizard.xml',
        'reports/cargo_collection_report.xml',
        'reports/logistic_invoice.xml',





    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}
