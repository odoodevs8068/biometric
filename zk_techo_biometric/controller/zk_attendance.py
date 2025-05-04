import json
from odoo import http, _
from odoo.addons.print_wizard.controller.date_filter import DateFilter
from odoo.http import content_disposition, dispatch_rpc, request
date_filter = DateFilter()


class ZKattendanceControllers(http.Controller):

    @http.route(['/zk_attendance_rep/excel_report/<model("zk_print_wizard"):report_id>', ], type='http', auth="user",
                csrf=False)
    def get_stock_product_excel_report(self, report_id=None, **args):
        date_from = report_id.date_from
        date_to = report_id.date_to
        emp_id = report_id.emp_id.bio_metric_user_id
        zk_device = request.env['zk_device']

        attendance_data = zk_device.get_transaction_data_using_api(date_from,date_to, str(emp_id))
        report_bytes = zk_device.prepare_attendance_reports(attendance_data, date_from, date_to)
        response = request.make_response(
            report_bytes,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition("Attendance Report" + '.xlsx'))
            ]
        )
        response.set_cookie('fileToken', 'dummy-because-api-expects-one')
        return response
