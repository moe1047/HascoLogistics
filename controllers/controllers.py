# -*- coding: utf-8 -*-
from odoo import http

class KalkaalLogistics(http.Controller):
    @http.route('/kalkaal_logistics/kalkaal_logistics/', auth='public')
    def index(self, **kw):
        return "Hello, world"

#     @http.route('/kalkaal_logistics/kalkaal_logistics/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('kalkaal_logistics.listing', {
#             'root': '/kalkaal_logistics/kalkaal_logistics',
#             'objects': http.request.env['kalkaal_logistics.kalkaal_logistics'].search([]),
#         })

#     @http.route('/kalkaal_logistics/kalkaal_logistics/objects/<model("kalkaal_logistics.kalkaal_logistics"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('kalkaal_logistics.object', {
#             'object': obj
#         })
