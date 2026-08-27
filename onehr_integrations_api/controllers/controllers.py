# -*- coding: utf-8 -*-
# from odoo import http


# class OnehrIntegrationsApi(http.Controller):
#     @http.route('/onehr_integrations_api/onehr_integrations_api', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/onehr_integrations_api/onehr_integrations_api/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('onehr_integrations_api.listing', {
#             'root': '/onehr_integrations_api/onehr_integrations_api',
#             'objects': http.request.env['onehr_integrations_api.onehr_integrations_api'].search([]),
#         })

#     @http.route('/onehr_integrations_api/onehr_integrations_api/objects/<model("onehr_integrations_api.onehr_integrations_api"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('onehr_integrations_api.object', {
#             'object': obj
#         })

