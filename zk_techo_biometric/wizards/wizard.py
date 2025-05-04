from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError, Warning


class PrintWizardInherit(models.TransientModel):
    _name = 'zk_print_wizard'

    emp_id = fields.Many2one('hr.employee')
    date_from = fields.Date(string='From', default=fields.Datetime.now)
    date_to = fields.Date(string='To', default=fields.Datetime.now)

    def button_print_report(self):
        return {
                'type': 'ir.actions.act_url',
                'url': '/zk_attendance_rep/excel_report/%s' % (self.id),
                'target': 'new',
            }


