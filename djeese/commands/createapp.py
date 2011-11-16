from collections import defaultdict
from djeese.apps import AppConfiguration, VALID_TYPES
from djeese.commands import BaseCommand
from djeese.utils import slugify, get_package_data
import re
import requests

class BaseValidator(object):
    """
    Base validator object.
    
    self.validate(value) calls self.check(value) and if not valid, prints
    self.message and return False. If valid, returns True
    """
    def validate(self, value):
        if not self.check(value):
            print self.message % value
            return False
        return True
    
    def check(self, value):
        return True


class URLValidator(BaseValidator):
    """
    Checks that a given URL is valid and can be accessed
    """
    message = "Could not open %r."
    
    def check(self, value):
        return requests.get(value, timeout=5).status_code == 200


class RegexValidator(BaseValidator):
    """
    Checks that a given value matches a regular expression
    """
    def __init__(self, regex, message, *flags):
        self.regex = re.compile(regex, *flags)
        self.message = message
    
    def check(self, value):
        return self.regex.match(value)


class SlugValidator(RegexValidator):
    """
    Checks that a given value is a slug (alphanumeric + underscores + dashes)
    """
    def __init__(self):
        super(SlugValidator, self).__init__(r'^[-\w]+$', "May only contain alphanumeric characters and dashes")


def ask(title, *validators, **kwargs):
    """
    Ask for a (single) value, validate using validators.
    
    If default is given, it will be returned if no input is given.
    
    If required is True, None is returned if no input is given.
    """
    default = kwargs.get('default', None)
    required = kwargs.get('required', True)
    if default:
        message = '%s [%s]: ' % (title, default)
    else:
        message = '%s: ' % title
    value = raw_input(message)
    if not value and default:
        return default
    if not value and not required:
        return None
    for validator in validators:
        if not validator.validate(value):
            return ask(title, *validators)
    return value

def ask_boolean(title, default=None):
    """
    Ask for a (single) boolean value.
    """
    if default is None:
        message = '%s [y/n]: ' % title
    elif default:
        message = '%s [Y/n]: ' % title
    else:
        message = '%s [y/N]: ' % title
    value = raw_input(message)
    if not value and default is not None:
        return 'true' if default else 'false'
    elif value in ['y', 'Y']:
        return 'true'
    elif value in ['n', 'N']:
        return 'false'
    print "Please enter either 'n' or 'y'"
    ask_boolean(title, default)

def ask_multi(title, minitems=0):
    """
    Ask for (at least) minitems values.
    """
    values = []
    while True:
        value = ask('%s (leave empty for next option)' % title, required=len(values) < minitems)
        if value:
            values.append(value)
        else:
            break
    # convert to string:
    if values:
        return '\n%s' % '    '.join(values)
    else:
        return None

def ask_choice(title, choices):
    """
    Make the user choose a single value from choices
    """
    choices_dict = dict([(str(index), choice) for index, choice in enumerate(choices)])
    print title
    for index, choice in enumerate(choices):
        print '(%s) %s' % (index, choice)
    value = ask("Please choose [0-%s]" % len(choices))
    while value not in choices_dict:
        print "Invalid choices"
        value = ask("Please choose [0-%s]" % len(choices))
    return choices_dict[value]

def contrib(config, section, key, method, *args, **kwargs):
    """
    Wrapper to ask the user for input using `method` (passing `args` and
    `kwargs` to that method) and if a value is returned, set it in the `config`
    under `section` and `key`.
    """
    value = method(*args, **kwargs)
    if value:
        config[section][key] = value
    return value


class Command(BaseCommand):
    help = 'Create a djeese apps.'

    def handle(self, **options):
        config = AppConfiguration(1)
        letterfirst = RegexValidator(r'^[a-zA-Z]', "Must start with a letter")
        name = contrib(config, 'app', 'name', ask, "Name", letterfirst)
        packagename = contrib(config, 'app', 'packagename', ask, 'Package name on PyPI', SlugValidator(), default=slugify(name))
        check_net = ask_boolean("Should we try to get additional information from djangopackages?", default=True)
        if check_net:
            data = get_package_data(packagename)
        else:
            data = defaultdict(lambda:None)
        contrib(config, 'app', 'url', ask, 'URL', default=data['url'])
        contrib(config, 'app', 'author', ask, 'Author', default=data['author'], required=False)
        contrib(config, 'app', 'author-url', ask, 'Author URL (optional)', default=data['author_url'], required=False)
        contrib(config, 'app', 'installed-apps', ask_multi, "Installed apps", minitems=1)
        contrib(config, 'app', 'version', ask, 'Version', default=data['version'])
        contrib(config, 'app', 'description', ask, 'Description (short)', default=data['description'])
        contrib(config, 'app', 'license', ask, 'License', default=data['license'])
        contrib(config, 'app', 'license-text', ask, 'License Text (URL)', URLValidator(), default=data['license_text_url'])
        contrib(config, 'app', 'translation-url', ask, 'URL to the translation page, eg transifex (optional)', URLValidator(), required=False)
        contrib(config, 'app', 'settings', ask_multi, 'Settings (optional)')
        for setting in config['app'].getlist('settings'):
            contrib(config, setting, 'name', ask, 'Name of the setting %r (Python)' % setting)
            contrib(config, setting, 'verbose-name', ask, 'Verbose name of the setting %r' % setting)
            contrib(config, setting, 'type', ask_choice, 'Type of the setting %r' % setting, choices=VALID_TYPES)
            contrib(config, setting, 'default', ask, 'Default value for setting %r (optional)' % setting, required=False)
            contrib(config, setting, 'required', ask_boolean, 'Is setting %r required' % setting, default=True)
            if config[setting].get('default', None):
                contrib(config, setting, 'editable', ask_boolean, 'Is setting %r editable' % setting, default=True)
        if ask_boolean("Does your application expose templates?", default=True) == 'true':
            while True:
                name = ask('Template path (eg %s/plugin.html)' % config['app']['packagename'])
                url = ask('URL to the source of the template', URLValidator())
                config['templates'][name] = url
                if ask_boolean("Are there more templates?") == 'false':
                    break
        fname = '%s.ini' % packagename
        config.write(fname)
