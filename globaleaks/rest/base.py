# -*- coding: UTF-8
#
#   rest/base
#   *********
#
#   Contains all the logic handle input and output validation.

import inspect
import json
from datetime import datetime
from globaleaks.rest.errors import InvalidInputFormat


uuid_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'

dateType = r'(.*)'
# contentType = r'(application|audio|text|video|image)'
# via stackoverflow:
# /^(application|audio|example|image|message|model|multipart|text|video)\/[a-zA-Z0-9]+([+.-][a-zA-z0-9]+)*$/
contentType = r'(.*)'

fileDict = {
            "name": unicode,
            "description": unicode,
            "size": int,
            "content_type": contentType,
            "date": dateType,
}

formFieldsDict = {
            "presentation_order": int,
            "label": unicode,
            "name": unicode,
            "required": bool,
            "hint": unicode,
            "type": unicode
}

