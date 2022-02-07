"""Inherited Product Template order model."""
from odoo import api, fields, models

class ProductTemplate(models.Model):
    """Product Template model."""

    _inherit = 'product.template'

    excise_percentage = fields.Float(string='Excise Percentage')
    duty_percentage = fields.Float(string='Duty Percentage')

