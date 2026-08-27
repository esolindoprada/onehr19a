# -*- coding: utf-8 -*-
# from odoo import http


# class OnehrPortalSelfService(http.Controller):
#     @http.route('/onehr_portal_self_service/onehr_portal_self_service', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/onehr_portal_self_service/onehr_portal_self_service/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('onehr_portal_self_service.listing', {
#             'root': '/onehr_portal_self_service/onehr_portal_self_service',
#             'objects': http.request.env['onehr_portal_self_service.onehr_portal_self_service'].search([]),
#         })

#     @http.route('/onehr_portal_self_service/onehr_portal_self_service/objects/<model("onehr_portal_self_service.onehr_portal_self_service"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('onehr_portal_self_service.object', {
#             'object': obj
#         })

