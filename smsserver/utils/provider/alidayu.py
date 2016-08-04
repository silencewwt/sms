# coding: utf-8
import datetime
from collections import OrderedDict
from hmac import HMAC
from requests.exceptions import RequestException

from smsserver.utils.provider.base import BaseClient, SMSSendFailed


class ALiDaYuClient(BaseClient):
    URL = 'https://eco.taobao.com/router/rest'
    DIGITS_DICT = {'0': u'零', '1': u'一', '2': u'二', '3': u'三', '4': u'四',
                   '5': u'五', '6': u'六', '7': u'七', '8': u'八', '9': u'九'}

    def __init__(self, apikey, secret, service_dict):
        self.apikey = apikey
        self.secret = secret
        self.service_dict = service_dict
        super(ALiDaYuClient, self).__init__()

    def send(self, country_code, phone_number, text, service_key):
        """
        :param country_code: 国家区号(阿里大于目前只能发+86的号码, 所以这个参数并无卵用)
        :param phone_number: 手机号码
        :param text: 文本内容
        :param service_key: 'sms' 或 'voice'
        :return: {'outid': u'z2c11bel02er'}
        """

        data = self._generate_data(phone_number, text, service_key)

        try:
            ret = self._requests_post(self.URL, data=data, timeout=5).json()
        except RequestException as e:
            raise SMSSendFailed(str(e))

        if 'error_response' in ret:
            error_messages = (ret['error_response']['code'],
                              ret['error_response']['msg'],
                              ret['error_response'].get('sub_code', ''),
                              ret['error_response'].get('sub_msg', ''))
            raise SMSSendFailed(u'阿里大于: %s %s %s %s' % error_messages)

        return {'outid': ret[self.service_dict[service_key]['keys']['response_key']]['request_id']}

    def _generate_data(self, phone_number, text, service_key):
        data = {
            'app_key': self.apikey,
            'timestamp': datetime.datetime.now().strftime('%F %T'),
            'format': 'json',
            'v': '2.0',
            'sign_method': 'hmac',
            self.service_dict[service_key]['keys']['phone_number_key']: phone_number
        }
        data.update(self.service_dict[service_key]['extra'])
        data.update(self._text_map(text, service_key))
        data['sign'] = self._generate_signature(data)
        return data

    def _text_map(self, text, service_key):
        """根据传入的 text 映射为阿里大于的模板 id && 模板变量"""
        for regex, param_template, template_code in self.service_dict[service_key]['regexs']:
            result = regex.search(text)
            if result:
                return {
                    self.service_dict[service_key]['keys']['templete_code_key']: template_code,
                    self.service_dict[service_key]['keys']['param_key']:
                        param_template % self._params_filter(result.groups(), service_key)

                }
        raise SMSSendFailed(u'阿里大于 无法匹配模板: %s' % text)

    def _generate_signature(self, data):
        ordered_data = OrderedDict(sorted(data.items(), key=lambda x: x[0]))
        params = []
        for key in ordered_data:
            params.append(key)
            params.append(ordered_data[key])
        return HMAC(self.secret, u''.join(params).encode('utf-8')).hexdigest().upper()

    def _params_filter(self, params, service_key):
        if service_key == 'sms':
            return params
        return self._digits_to_chinese(params[0])  # params: ('123456', )

    def _digits_to_chinese(self, digits):
        return u''.join([self.DIGITS_DICT[digit] for digit in digits])
