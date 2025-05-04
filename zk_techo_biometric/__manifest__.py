{
    'name': 'ZK Biometric Integration',
    'version': '1.2',
    'sequence': 100,
    'author': "JD DEVS",
    'category': '',
    'depends': ['base', 'hr_attendance', 'hr', 'mail', 'web', 'print_wizard'],
    'data': [
        "security/ir.model.access.csv",
        "views/zk_device.xml",
        "views/settings.xml",
        "views/hr.xml",
        "wizards/wizard.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'images': ['static/description/assets/screenshots/banner.png'],

}
