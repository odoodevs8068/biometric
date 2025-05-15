import requests
import datetime
from psycopg2 import connect
from pytz import timezone, all_timezones
from odoo.exceptions import ValidationError, UserError, Warning
from zk import ZK
import json
import base64
import threading
from threading import Thread
import time
import pytz
from zk.exception import ZKErrorResponse
from odoo import api, fields, models, registry, _
from datetime import datetime
import io
import xlsxwriter
from collections import defaultdict
from datetime import datetime, timedelta


AUTH_API = "/api-token-auth/"
DEVICE_OBJ = "/iclock/api/terminals/?sn=%s"
Area_Api = f"/personnel/api/areas/"

_listener_started = False
import logging

_logger = logging.getLogger(__name__)

class ZKDevice(models.Model):
    _name = 'zk_device'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Biometric Device"

    ipaddress = fields.Char(string="Machine IP", tracking=True)
    port = fields.Integer(string="Machine Name", tracking=True)
    company_id = fields.Many2one('res.company',readonly=1, default=lambda self: self.env.user.company_id.id, string='Company')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    name = fields.Char(string='Device Name', readonly=1, tracking=True)
    serial = fields.Char(string='Device Serial No.', readonly=1, tracking=True)
    version = fields.Char(string='Device Version', readonly=1, tracking=True)
    fp_version = fields.Char(string="Fingerprint Version" , readonly=1, tracking=True)
    face_version = fields.Char(string="Face Version", readonly=1, tracking=True)
    device_state = fields.Boolean(string='Enable Device', readonly=1, tracking=True)
    device_id = fields.Integer()
    branch_area = fields.Char(string='Area Name',  tracking=True)

    def check_device_conf(self):
        if not self.ipaddress:
            raise ValidationError(_(f"Sorry, Please Fill the IP Address To connect The Device {self.name}"))
        if not self.port:
            raise ValidationError(_(f"Sorry, Please Fill the Port Number To connect The Device {self.name}"))

    def disable_device(self):
        """Disable The Device"""
        zk = ZK(self.ipaddress, port=self.port, password=0, force_udp=False)
        try:
            conn = zk.connect()
            if conn.disable_device():
                self.device_state = False
        except Exception as e:
            raise ValidationError(_(f"Failed to Disable The Device: {str(e)}"))

    def test_connection_device(self):
        zk = ZK(self.ipaddress, port=self.port, password=0, force_udp=False, ommit_ping=True)
        try:
            conn = zk.connect()
            self.name = conn.get_device_name()
            self.serial = conn.get_serialnumber()
            self.version = conn.get_firmware_version()
            self.fp_version = conn.get_fp_version()
            self.face_version = conn.get_face_version()
            self.device_state = conn.enable_device()

            self.env['bus.bus']._sendone(self.user_id.partner_id, 'simple_notification', {
                'title': _(f'Device {self.name}'),
                'message': _('Connected Successfully'),
                'sticky': False,
                'success': True
            })
            self._register_hook()
        except Exception as e:
            self.device_state = False
            _logger = logging.getLogger(__name__)
            _logger.error(f"Connection failed: {str(e)}\n {zk.helper.test_ping()}")
            raise ValidationError(_(f"Failed: %s \n TEST PEING {str(zk.helper.test_ping())}\n") % str(e))

    def _register_hook(self):
        """Start listener on Odoo startup"""
        super()._register_hook()
        _logger.info("Starting real-time attendance listener at startup...")
        thread = threading.Thread(target=self.real_time_attendance_listener, daemon=True)
        thread.start()

    def start_real_time_attendance_listener(self):
        """Start a separate thread to continuously fetch attendance"""
        _logger.info("Starting real-time attendance listener...")
        thread = threading.Thread(target=self.real_time_attendance_listener, daemon=True)
        thread.start()

    def real_time_attendance_listener(self):
        """Continuously fetch attendance from the biometric device"""
        while True:
            with self.pool.cursor() as cr:
                new_env = api.Environment(cr, self.env.uid, self.env.context)
                device_model = self.with_env(new_env)
                devices = device_model.search([('device_state', '=', True)])
                for device in devices:
                    try:
                        device.get_machine_real_time_attendance()
                    except Exception as e:
                        _logger.error(f"Failed to fetch real-time attendance: {str(e)}")
                cr.commit()
            time.sleep(5)

    def get_machine_real_time_attendance(self):
        zk = ZK(self.ipaddress, port=self.port, password=0, force_udp=False)
        try:
            conn = zk.connect()
            _logger.info(f"Connected to device {self.name} at {self.ipaddress}:{self.port}")
            conn.enable_device()
            print("Connected Successfully!")
            for attendance in conn.live_capture():
                if attendance and attendance.uid:
                    emp_id = self.env['hr.employee'].search([('bio_metric_user_id', '=', attendance.user_id)], limit=1)
                    if attendance.punch == 0 and emp_id:
                        attend_query = f"""
                            INSERT INTO hr_attendance (
                            employee_id,
                            check_in,
                            create_uid,
                            create_date,
                            write_uid,
                            write_date
                        ) VALUES (
                             {emp_id.id},
                             '{datetime.now()}',
                            1,
                            NOW(),
                            1,
                            NOW()
                        );
                        """
                        self._cr.execute(attend_query)
                    elif attendance.punch == 1 and emp_id:
                        chech_out = self.env['hr.attendance'].search([
                            ('employee_id', '=', emp_id.id),
                            ('check_out', '=', False),
                        ])
                        if chech_out:
                            check_in = chech_out.check_in
                            worked_hours = 0.0
                            current_time = datetime.datetime.now()
                            if check_in:
                                delta = current_time - check_in
                                worked_hours = delta.total_seconds() / 3600.0
                            update_query = f"""
                                UPDATE hr_attendance
                                    SET check_out = NOW(),
                                        write_date = NOW(), worked_hours = '{worked_hours}',
                                    WHERE id = {chech_out.id};
                            """
                            self._cr.execute(update_query)
                    self.env.cr.commit()
                    _logger.info(f"Punch recorded:")
            conn.disconnect()
        except Exception as e:
            _logger.error(f"Failed to fetch real-time attendance from {self.ipaddress}: {str(e)}")


#################### API CALL FUNCTIONS #####################################################################################
    def button_open_print_wizard(self):
        return {
            'name': 'Print Attendance Report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'zk_print_wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def get_transaction_data_using_api(self, date_from,date_to, emp_code):
        config = self.env['res.config.settings']
        Headers = config.PrepareHeaders()
        url = config.get_based_url() + (
            f"/iclock/api/transactions/"
            f"?start_time={date_from}"
            f"&end_time={date_to}&emp_code={emp_code}"
        )
        try:
            response = requests.get(url, headers=Headers)
            decoded = response.json()
            de_data = decoded.get('data', [])
            if decoded['count'] == 0:
                raise ValidationError(_("There Is No Attendace For This Employee in Device"))
            if decoded.get('next'):
                de_data = self.next_page_data(decoded['next'], Headers, de_data)
                print("de_data", json.dumps(de_data, indent=4))
                return de_data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed To Connect The API: {e}")

    def next_page_data(self, url, Headers, de_data):
        response = requests.get(url, headers=Headers)
        try:
            decoded = response.json()
            de_data.extend(decoded['data'])
            if decoded['next']:
                return self.next_page_data(decoded['next'], Headers, de_data)
            return de_data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed To Connect The API: {e}")

    def prepare_attendance_reports(self, attendance_data, date_from, date_to):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        worksheet.set_column('A:AZ', 20)
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9D9D9',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        worksheet.write('A1', 'Employee Name', header_format)
        worksheet.write('B1', 'Check In Time', header_format)
        worksheet.write('C1', 'Check Out Time', header_format)
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:C', 22)
        attendance_by_date = defaultdict(lambda: {'check_in': None, 'check_out': None})
        employee_name = ""
        for record in attendance_data:
            punch_time_str = record.get('punch_time')
            punch_time = datetime.strptime(punch_time_str, '%Y-%m-%d %H:%M:%S')
            date_key = punch_time.date()
            if not employee_name:
                employee_name = (record.get('first_name') or '') + (
                    ' ' + record.get('last_name') if record.get('last_name') else '')
            if record.get('punch_state') == "0":  # Check In
                if attendance_by_date[date_key]['check_in'] is None or punch_time < datetime.strptime(
                        attendance_by_date[date_key]['check_in'], '%Y-%m-%d %H:%M:%S'):
                    attendance_by_date[date_key]['check_in'] = punch_time_str
            elif record.get('punch_state') == "1":  # Check Out
                if attendance_by_date[date_key]['check_out'] is None or punch_time > datetime.strptime(
                        attendance_by_date[date_key]['check_out'], '%Y-%m-%d %H:%M:%S'):
                    attendance_by_date[date_key]['check_out'] = punch_time_str
        start_date = date_from
        end_date = date_to
        current_date = start_date
        row = 1
        while current_date <= end_date:
            check_in = attendance_by_date[current_date]['check_in'] if attendance_by_date[current_date][
                'check_in'] else ''
            check_out = attendance_by_date[current_date]['check_out'] if attendance_by_date[current_date][
                'check_out'] else ''
            worksheet.write(row, 0, employee_name.strip())
            worksheet.write(row, 1, check_in)
            worksheet.write(row, 2, check_out)
            row += 1
            current_date += timedelta(days=1)

        workbook.close()
        output.seek(0)
        return output.read()

###############################################################################################################################################################################

class Area(models.Model):
    _name = "zk_device_area"
    _description = "Device Area"
    _rec_name = 'area_name'

    area_id = fields.Integer('Area ID')
    area_code = fields.Char('Area Code')
    area_name = fields.Char('Area Name')

    def check_area(self):
        if not self.area_code or not self.area_name:
            raise ValidationError(_("Before Create The Area Please Choose Area name/Area Code"))

    def create_area(self):
        self.check_area()
        config = self.env['res.config.settings']
        payload = {'area_code': self.area_code, 'area_name': self.area_name}
        data = config.create_record_device( Area_Api, payload)
        if 'id' in data:
            self.area_id = data['id']
            mssge = f"Area '{self.area_name}' Created Successfully",
            notify = config.get_success_return(mssge)
            return notify

    def update_area(self):
        self.check_area()
        if not self.area_id:
            raise ValidationError(_("To update Area Make Sure It is In Device or Get The Area First"))
        config = self.env['res.config.settings']
        payload = { 'area_code': self.area_code,'area_name': self.area_name}
        data = config.update_record_device(f"{Area_Api}/{self.area_id}/", payload)
        if data:
            mssge = f"Area '{self.area_name}' Updated Successfully",
            notify = config.get_update_return(mssge)
            return notify

    def delete_area(self):
        if not self.area_id:
            raise ValidationError(_("Sorry , unable To Do the Delete Process"))
        config = self.env['res.config.settings']
        api = f"{Area_Api}/{self.area_id}/"
        data = config.delete_record_device(api)
        if data == 204:
            self.area_id = 0

