# -*- coding: utf-8 -*-
# from odoo import http


# class OnehrRetirementOffboarding(http.Controller):
#     @http.route('/onehr_retirement_offboarding/onehr_retirement_offboarding', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/onehr_retirement_offboarding/onehr_retirement_offboarding/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('onehr_retirement_offboarding.listing', {
#             'root': '/onehr_retirement_offboarding/onehr_retirement_offboarding',
#             'objects': http.request.env['onehr_retirement_offboarding.onehr_retirement_offboarding'].search([]),
#         })

#     @http.route('/onehr_retirement_offboarding/onehr_retirement_offboarding/objects/<model("onehr_retirement_offboarding.onehr_retirement_offboarding"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('onehr_retirement_offboarding.object', {
#             'object': obj
#         })

