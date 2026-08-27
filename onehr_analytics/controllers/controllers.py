# -*- coding: utf-8 -*-
# from odoo import http


# class OnehrAnalytics(http.Controller):
#     @http.route('/onehr_analytics/onehr_analytics', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/onehr_analytics/onehr_analytics/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('onehr_analytics.listing', {
#             'root': '/onehr_analytics/onehr_analytics',
#             'objects': http.request.env['onehr_analytics.onehr_analytics'].search([]),
#         })

#     @http.route('/onehr_analytics/onehr_analytics/objects/<model("onehr_analytics.onehr_analytics"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('onehr_analytics.object', {
#             'object': obj
#         })

