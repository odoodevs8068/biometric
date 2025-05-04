from odoo import api, models, fields


class ZkpunchHistory(models.Model):
    _name = 'zk_punch_log'

    punch_state = fields.Char()
    punch_date = fields.Datetime()
    user_id = fields.Char()
    emp_id = fields.Many2one('hr.employee')
    attendance_id = fields.Many2one('hr.employee')