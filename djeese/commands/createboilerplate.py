from __future__ import with_statement
from djeese.boilerplates import BoilerplateConfiguration, VALID_TYPES
from djeese.commands import BaseCommand
from djeese.commands.createapp import guess_license_path
from djeese.input_helpers import (contrib, ask, letterfirst, PathValidator, 
    ask_multi, RegexValidator, ask_choice, ask_boolean)

class Command(BaseCommand):
    help = 'Create a djeese boilerplate'
    
    def handle(self, **options):
        config = BoilerplateConfiguration(1)
        contrib(config, 'boilerplate', 'name', ask, "Name", letterfirst)
        contrib(config, 'boilerplate', 'url', ask, 'Project URL (optional)', required=False)
        contrib(config, 'boilerplate', 'author', ask, 'Author')
        contrib(config, 'boilerplate', 'author-url', ask, 'Author URL (optional)', required=False)
        contrib(config, 'boilerplate', 'version', ask, 'Version')
        contrib(config, 'boilerplate', 'description', ask, 'Description (short)')
        contrib(config, 'boilerplate', 'license', ask, 'License')
        contrib(config, 'boilerplate', 'license-path', ask, 'Path to license file', PathValidator(), default=guess_license_path())
        contrib(config, 'boilerplate', 'settings', ask_multi, 'Settings (optional)')
        for setting in config['boilerplate'].getlist('settings'):
            contrib(config, setting, 'name', ask, 'Name of the setting %r' % setting, RegexValidator(r'[a-zA-Z_]+', "Can only contain letters and underscores"))
            contrib(config, setting, 'verbose-name', ask, 'Verbose name of the setting %r' % setting)
            contrib(config, setting, 'type', ask_choice, 'Type of the setting %r' % setting, choices=VALID_TYPES)
            default = contrib(config, setting, 'default', ask, 'Default value for setting %r (optional)' % setting, required=False)
            config[setting]['required'] = str(not default).lower()
        print "Configuring CMS templates. Only list templates that should be selectable in the CMS"
        while True:
            name = ask('Verbose template name')
            path = ask('Path to the source of the template', PathValidator('templates'))
            config['templates'][path] = name
            if ask_boolean("Are there more templates?") == 'false':
                break

        config.write('boilerplate.ini')