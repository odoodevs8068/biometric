import json
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError, Warning

Emp_api = f"/personnel/api/employees/"
Dept_api = f"/personnel/api/departments/"
Posti_api = f"/personnel/api/positions/"


class HrEmplyeeInherited(models.Model):
    _inherit = 'hr.employee'

    bio_metric_user_id = fields.Integer()
    bio_metric_emp_id = fields.Integer()
    bio_metric_area_id = fields.Many2one('zk_device_area')

    def button_open_print_wizard(self):
        if self.bio_metric_user_id == 0:
            raise ValidationError(_("Employee Biometric User Code Is Missing"))
        return {
            'name': 'Print Attendance Report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'zk_print_wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_emp_id': self.id,
            }
        }

    def prepare_payload(self):
        payload = {
                "emp_code": str(self.bio_metric_user_id),
                "first_name": self.name,
                "format_name": f"{str(self.bio_metric_user_id)} {self.name}",
                "full_name": self.name,
                "verify_mode": 0,
                "mobile": self.mobile_phone,
                "email": self.work_email,
                "area": []
                }
        self.check_dep_area(payload)
        return payload

    def check_dep_area(self, payload):
        if self.department_id and self.department_id.zk_dep_id:
            payload['department'] = int(self.department_id.zk_dep_id)
        if self.bio_metric_area_id and self.bio_metric_area_id.area_id:
            payload['area'].append(int(self.bio_metric_area_id.area_id))
        else:
            raise ValidationError("To Create a Employee Area ID Is Required")
        return payload

    def button_create_employee(self):
        """CREATE EMPLOYEE ON ZK BIOMETRIC DEVICE"""
        config = self.env['res.config.settings']
        payload = self.prepare_payload()
        data = config.create_record_device(Emp_api, payload)
        if data:
            if 'id' in data:
                self.bio_metric_emp_id = data['id']
                mssge = f"Employee '{self.name}' Created Successfully",
                notify = config.get_success_return(mssge)
                return notify
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"Employee Creation Failed",
                    'type': 'warning',
                    'sticky': False
                }
            }

    def check_bio_metric_emp_id(self):
        if not self.bio_metric_emp_id:
            raise ValidationError(_("Sorry, Unable To Do the Process Zk Emoloyee ID in Empty/Zero"))

    def button_update_emp(self):
        """UPDATE EMPLOYEE ON ZK BIOMETRIC DEVICE"""
        self.check_bio_metric_emp_id()
        config = self.env['res.config.settings']
        payload = self.prepare_payload()
        data = config.update_record_device(f"{Emp_api}/{self.bio_metric_emp_id}/", payload)
        if data:
            if 'first_name' in data and data['first_name'] == self.name:
                mssge = f"Employee '{self.name}' Updated Successfully",
                notify = config.get_update_return(mssge)
                return notify
            else:
                raise ValidationError("Sorry, Something Went wrong Update Name Is Not Matching With Current Name")
        else:
            raise ValidationError("Sorry, Nothing To Update \n\n Please Contact Your Administrator")

    def delete_emp_device(self):
        self.check_bio_metric_emp_id()
        config = self.env['res.config.settings']
        api = f"{Emp_api}/{self.bio_metric_emp_id}/"
        data = config.delete_record_device(api)
        if data == 204:
            self.bio_metric_emp_id = 0

class Departments(models.Model):
    _inherit = 'hr.department'

    zk_dep_id = fields.Integer('Zk Department ID')
    zk_dept_code = fields.Char('Zk Department Code')

    def check_depart(self):
        if not self.zk_dept_code or not self.name:
            raise ValidationError(_("Please Fill The Department Code Or Name"))

    def dept_payload(self):
        return {'dept_code': self.zk_dept_code, 'dept_name': self.name}

    def create_departments(self):
        self.check_depart()
        config = self.env['res.config.settings']
        data = config.create_record_device(Dept_api, self.dept_payload())
        if data and 'id' in data:
            self.zk_dep_id = data['id']
            mssge = f"Department '{self.name}' Created Successfully",
            notify = config.get_success_return(mssge)
            return notify

    def check_zk_dep_id(self):
        if not self.zk_dep_id:
            raise ValidationError(_("Sorry , Unable To Do the Process Zk Department ID in Empty/Zero"))

    def update_department(self):
        self.check_depart()
        self.check_zk_dep_id()
        config = self.env['res.config.settings']
        data = config.update_record_device(f"{Dept_api}/{self.zk_dep_id}/", self.dept_payload())
        if data:
            mssge = f"Department '{self.name}' Updated Successfully",
            notify = config.get_update_return(mssge)
            return notify

    def delete_department(self):
        self.check_zk_dep_id()
        config = self.env['res.config.settings']
        api = f"{Dept_api}/{self.zk_dep_id}/"
        data = config.delete_record_device(api)
        if data == 204:
            self.zk_dep_id = 0

class JobpositionInherit(models.Model):
    _inherit = 'hr.job'

    zk_job_id = fields.Integer('ZK Position ID')
    zk_job_code = fields.Char('ZK Job Code')

    def check_position(self):
        if not self.zk_job_code or not self.name:
            raise ValidationError(_("Please Fill The Job Position Code Or Name"))

    def job_payload(self):
        return  {'position_code': self.zk_job_code, 'position_name': self.name}

    def create_position(self):
        self.check_position()
        config = self.env['res.config.settings']
        data = config.create_record_device(Posti_api, self.job_payload())
        if data and 'id' in data:
            self.zk_job_id = data['id']
            mssge = f"Position '{self.name}' Created Successfully",
            notify = config.get_success_return(mssge)
            return notify

    def check_zk_job_id(self):
        if not self.zk_job_id:
            raise ValidationError(_("Sorry , Unable To Do the Process Zk Position ID in Empty/Zero"))

    def update_position(self):
        self.check_position()
        self.check_zk_job_id()
        config = self.env['res.config.settings']
        data = config.update_record_device(f"{Posti_api}/{self.zk_job_id}/", self.job_payload())
        if data:
            mssge = f"Job Position '{self.name}' Updated Successfully",
            notify = config.get_update_return(mssge)
            return notify

    def delete_position(self):
        self.check_zk_job_id()
        config = self.env['res.config.settings']
        api = f"{Posti_api}/{self.zk_job_id}/"
        data = config.delete_record_device(api)
        if data == 204:
            self.zk_job_id = 0