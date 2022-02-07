"""inherit the stock landed cost lines model."""

from odoo import fields, models, tools, _
from odoo.addons.stock_landed_costs.models import stock_landed_cost as slc

slc.SPLIT_METHOD.append(('by_duty','By Duty'))
slc.SPLIT_METHOD.append(('by_excise','By Excise'))
print("-------------------",slc.SPLIT_METHOD)

class StockLandedCostLine(models.Model):
    """inherit the stock landed cost lines model."""

    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(help="Equal : Cost will be equally divided.\n"
             "By Quantity : Cost will be divided according to product's quantity.\n"
             "By Current cost : Cost will be divided according to product's current cost.\n"
             "By Weight : Cost will be divided depending on its weight.\n"
             "By Volume : Cost will be divided depending on its volume.\n"
             "By Duty : Cost will be divided depending on its duty.\n"
             "By Excise : Cost will be divided depending on its Excise.")



class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'


    def get_valuation_lines(self):
        result = super().get_valuation_lines()
        for rec in result:
            stock_move_obj = self.env['stock.move'].search([('id', '=', rec.get('move_id'))])
            rec['excise_percentage'] = stock_move_obj.product_id.excise_percentage
            rec['duty_percentage'] = stock_move_obj.product_id.duty_percentage
            rec['po_cost'] = stock_move_obj.stock_valuation_layer_ids.mapped('value')[0]
        return result

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()
        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            total_duty = 0.0
            total_excise = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                total_excise += val_line_values.get('excise_percentage',0.0)*val_line_values.get('po_cost',0.0)
                total_duty += val_line_values.get('duty_percentage', 0.0)*val_line_values.get('po_cost',0.0)
                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)
                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit

                        elif line.split_method == 'by_excise' and total_excise:
                            per_unit = (line.price_unit / total_excise)
                            value = valuation.excise_percentage * valuation.po_cost * per_unit

                        elif line.split_method == 'by_duty' and total_duty:
                            per_unit = (line.price_unit / total_duty)
                            value = valuation.duty_percentage * valuation.po_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)
                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value
                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True



class AdjustmentLines(models.Model):

    _inherit = 'stock.valuation.adjustment.lines'

    excise_percentage = fields.Float(string='Excise Percentage')
    duty_percentage = fields.Float(string='Duty Percentage')
    po_cost = fields.Float(string='Purchase Order Cost')


