from odoo import api, models, fields, _
import requests
from odoo.exceptions import ValidationError, UserError, Warning
import json
import logging


_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    server_ip = fields.Char(string='Server IP', config_parameter='zk_techo_biometric.server_ip')
    server_port = fields.Integer(string="Server Port", config_parameter='zk_techo_biometric.server_port')
    user_name = fields.Char(string="User Name", config_parameter='zk_techo_biometric.user_name')
    password = fields.Char(string="Password", config_parameter='zk_techo_biometric.password')
    auth_token = fields.Char('Auth Token', config_parameter='zk_techo_biometric.auth_token')

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('zk_techo_biometric.server_ip', self.server_ip)
        self.env['ir.config_parameter'].sudo().set_param('zk_techo_biometric.server_port', self.server_port)
        self.env['ir.config_parameter'].sudo().set_param('zk_techo_biometric.user_name', self.user_name)
        self.env['ir.config_parameter'].sudo().set_param('zk_techo_biometric.password', self.password)
        self.env['ir.config_parameter'].sudo().set_param('zk_techo_biometric.auth_token', self.auth_token)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(
            server_ip=ICPSudo.get_param('zk_techo_biometric.server_ip'),
            server_port=ICPSudo.get_param('zk_techo_biometric.server_port'),
            user_name=ICPSudo.get_param('zk_techo_biometric.user_name'),
            password=ICPSudo.get_param('zk_techo_biometric.password'),
            auth_token=ICPSudo.get_param('zk_techo_biometric.auth_token'),
        )
        return res

    def get_credentials(self):
        user_name = self.env['ir.config_parameter'].sudo().get_param('zk_techo_biometric.user_name')
        password = self.env['ir.config_parameter'].sudo().get_param('zk_techo_biometric.password')
        return user_name, password

    def button_get_auth_token(self):
        user_name, password = self.get_credentials()
        url = f"{self.get_based_url()}/api-token-auth/"
        headers = {"Content-Type": "application/json"}
        payload = {"username": user_name,"password": password}
        response = requests.post(url, headers=headers, json=payload)
        try:
            decoded = response.json()
            if 'token' in decoded:
                self.auth_token = decoded['token']
                self.env['ir.config_parameter'].sudo().set_param('zk_techo_biometric.auth_token', decoded['token'])
        except json.JSONDecodeError as e:
            raise ValidationError("Failed To Connect The API:", e)

    def get_access_token(self):
        token = self.env['ir.config_parameter'].sudo().get_param('zk_techo_biometric.auth_token')
        if token:
            return token
        else:
            raise ValidationError(_('You Dont Have Auth Token To Get Data \n Please Contact Your Administrator'))

    def PrepareHeaders(self):
        token = self.get_access_token()
        Headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {token}"
        }
        return Headers

    def get_based_url(self):
        server_ip = self.env['ir.config_parameter'].sudo().get_param('zk_techo_biometric.server_ip')
        server_port = self.env['ir.config_parameter'].sudo().get_param('zk_techo_biometric.server_port')
        if server_ip and server_port:
            return f"http://{server_ip}:{server_port}"
        else:
            raise ValidationError(_('Server IP/Port Missing'))

    def create_record_device(self, api, payload):
        url = self.get_based_url() + api
        HEADERS = self.PrepareHeaders()
        try:
            response = requests.post(url, json=payload, headers=HEADERS)
            try:
                print("response.status", response.status_code)
                decoded = response.json()
                print("decoded", decoded)
                return decoded
            except ValueError:
                raise ValidationError("Response content is not valid JSON: %s", response.text)
        except requests.exceptions.RequestException as e:
            raise ValidationError(f"Request to create Method failed: {str(e)}")

    def update_record_device(self, api, payload):
        url = self.get_based_url() + api
        HEADERS = self.PrepareHeaders()
        try:
            response = requests.patch(url, json=payload, headers=HEADERS)
            response.raise_for_status()
            try:
                if response.status_code == 200:
                    return  response.json()
            except ValueError:
                raise ValidationError("Response content is not valid JSON: %s", response.text)
        except requests.exceptions.RequestException as e:
            raise ValidationError("Request to create area failed: %s", str(e))

    def delete_record_device(self, api):
        url = self.get_based_url() + api
        HEADERS = self.PrepareHeaders()
        try:
            response = requests.delete(url, headers=HEADERS)
            response.raise_for_status()
            try:
                if response.status_code == 204:
                    return  response.status_code
            except ValueError:
                raise ValidationError("Response content is not valid JSON: %s", response.text)
        except requests.exceptions.RequestException as e:
            raise ValidationError("Request to create area failed: %s", str(e))

    def get_success_return(self, message):
        notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"{message}",
                    'type': 'success',
                    'sticky': False,
                }
            }
        return notification

    def get_update_return(self, message):
        notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"{message}",
                    'type': 'info',
                    'sticky': False,
                }
            }
        return notification