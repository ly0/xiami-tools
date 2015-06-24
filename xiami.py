# -*- coding: utf-8 -*-

import sys
from urllib2 import unquote
import json
import time
import re
import logging
from functools import partial
import xmltodict
import requests
from BeautifulSoup import BeautifulSoup
import captcha

logger = logging.getLogger()
formatter = logging.Formatter(
    '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',)
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.setLevel(logging.NOTSET)

reload(sys)
sys.setdefaultencoding('utf-8')


class Xiamiexp(Exception):
    """
    异常类
    """
    def __init__(self, err):
        super(Xiamiexp, self).__init__()
        self.err = err

    def __str__(self):
        return self.err_type()

    def __expr__(self):
        return self.__str__()

    def err_type(self):
        """
        xiami_account 虾米帐号密码错误

        taobao_account 淘宝帐号密码错误
        taobao_captcha 淘宝帐号验证码输入错误
        """

        if self.err == 'xiami_account':
            return u'虾米帐号密码错误'
        elif self.err == 'taobao_account':
            return u'淘宝帐号密码输入错误'
        elif self.err == 'taobao_captcha':
            return u'淘宝验证码输入错误'
        elif self.err == 'generic_user_err':
            return u'Cookies 无效, 请确认用户名密码或者 cookies 的有效性.'



class Utils:

    @staticmethod
    def text_validate(text):
        return text.replace('\'', '').replace('\\', '').replace('/', '')

    @staticmethod
    def url_decrypt(s):
        start = s.find('h')
        row = int(s[0:start])
        length = len(s[start:])
        column = length / row
        output = ''
        real_s = list(s[1:])

        sucks = []
        suck = length % row  # = 0 -> good! if not , sucks!
        for i in range(1, suck + 1):
            sucks.append(real_s[i * (column)])
            real_s[i * (column)] = 'sucks'
            real_s.remove('sucks')
        for i in range(column):
            output += ''.join(real_s[i:][slice(0, length, column)])
        output += ''.join(sucks)
        return unquote(output).replace('^', '0')

    @staticmethod
    def check_username(func, *args):
        def _wrapper(*args):
            obj = args[0]
            if (not obj.username or not obj.password) and not obj.taobao:
                logger.debug('用户未登录')
                raise Exception('用户未登录')
            else:
                return func(*args)
        return _wrapper

    header = {'User-Agent': 'Mozilla/5.0',
              'Referer': 'http://img.xiami.com/static/swf/seiya/player.swf?v=1394535902294'}


class Xiamibase(object):
    """基类定义了基本的get和post访问
    """
    header = {'User-Agent': 'Mozilla/5.0',
              'Referer': 'http://img.xiami.com/static/swf/seiya/player.swf?v=1394535902294'}

    def __init__(self, captcha_handler=None):
        self.session = requests.session()
        self.captcha_handler = self._captcha_handler
        if captcha_handler:
            self.captcha_func = captcha_handler
        else:
            self.captcha_func = captcha.show

    def _safe_get(self, *args, **kwargs):
        while True:
            try:
                data = self.session.get(*args, **kwargs)

                if data.status_code == 403:
                    sec = re.findall('<script>document.cookie="sec=(.*?);', data.content)
                    if len(sec) != 0:
                        self.session.cookies['sec'] = sec[0]
                        logger.debug('403 update sec=' + sec[0])
                        continue
            except Exception as e:
                # 失败重试
                logger.error('Exception in _safe_get:' + str(e))
                continue

            if 'regcheckcode.taobao.com' in data.content:
                print 'Captcha needed.'
                # 目前只是把整个requests.Response和session对象传给验证码处理函数, 函数需自行处理完后重试.
                self.captcha_handler(self.session, data)
                continue
            return data

    def _safe_post(self, *args, **kwargs):
        while True:
            try:
                data = self.session.post(*args, **kwargs)

                if data.status_code == 403:
                    sec = re.findall('<script>document.cookie="sec=(.*?);', data.content)
                    if len(sec) != 0:
                        self.session.cookies['sec'] = sec[0]
                        logger.debug('403 ' + 'update sec=', sec[0])
                        continue
            except Exception as e:
                # 失败重试
                logger.error('Exception in _safe_get:' + str(e))
                continue

            if 'regcheckcode.taobao.com' in data.content:
                # 目前只是把整个requests.Response和session对象传给验证码处理函数, 函数需自行处理完后重试.
                self.captcha_handler(self.session, data)
                continue
            return data

    def _get_captcha(captcha_data):
        captcha.show(captcha_data)
        code = raw_input('captcha >')
        return code

    def _captcha_handler(self, *args, **kwargs):

        session = args[0]
        html = args[1].text
        bs = BeautifulSoup(html)
        captcha_url = bs.find('img')['src']
        input_session_id = bs.find('input', {'name': 'sessionID'})['value']
        input_apply = bs.find('input', {'name': 'apply'})['value']
        input_referer = bs.find('input', {'name': 'referer'})['value']

        header = {'Referer': input_referer,
                  'User-Agent': 'Mozilla/5.0'}

        captcha_data = session.get(captcha_url, headers=header).content

        code = self.captcha_func(captcha_data)
        """
        if handler:
            code = handler(captcha_data)
        else:
            captcha.show(captcha_data)
            code = raw_input('captcha >')
        """

        url = 'http://www.xiami.com/alisec/captcha/tmdgetv3.php'
        data = {'code': code,
                'sessionID': input_session_id,
                'apply': input_apply,
                'referer': input_referer}

        ret = session.post(url, data=data, headers=header)



class Xiami(Xiamibase):
    """Xiami类定义了虾米的登录和操作"""
    def __init__(self, username=None, password=None,
                 taobao=False, cookies=None, *args, **kwargs):
        super(Xiami, self).__init__(*args, **kwargs)
        self.account = {}
        self.hq = False
        self.username = username
        self.password = password

        if not taobao and not cookies:
            self.from_xiami(username, password)

        if taobao:
            self.from_taobao(username, password)

        if cookies:
            self.from_cookies(cookies)

        try:
            self._get_uid()
        except:
            raise Xiamiexp('generic_user_err')


    def from_xiami(self, username, password):
        """虾米帐号登录, 需要没有绑定淘宝帐号
        该登录方式即将被虾米废弃
        """
        header = {'user-agent': 'Mozilla/5.0'}
        login_url = 'https://login.xiami.com/member/login'
        data = {'email': username,
                'password': password,
                'done': 'http://www.xiami.com/account',
                'submit': '登 录'
                }

        ret = self._safe_post(login_url, data=data, headers=header)
        """
        try:
            self._get_uid()
        except:
            logger.debug('用户名或者密码错误, 视为没有登录')
        """

    def from_taobao(self, username, password):
        """淘宝帐号登录, username 为淘宝帐号, password为支付宝帐号
        注意不要和 alipay 帐号弄混了
        """
        captcha = ''
        url = 'https://passport.alipay.com/mini_login.htm?lang=&appName=xiami&appEntrance=taobao&cssLink=&styleType=vertical&bizParams=&notLoadSsoView=&notKeepLogin=&rnd=0.6477347570091512?lang=zh_cn&appName=xiami&appEntrance=taobao&cssLink=https%3A%2F%2Fh.alipayobjects.com%2Fstatic%2Fapplogin%2Fassets%2Flogin%2Fmini-login-form-min.css%3Fv%3D20140402&styleType=vertical&bizParams=&notLoadSsoView=true&notKeepLogin=true&rnd=0.9090916193090379'
        bs = BeautifulSoup(self._safe_get(url).content)

        while True:
            data = {'loginId': username,
                'password': password,
                'appName': 'xiami',
                'appEntrance': 'taobao',
                'hsid': bs.find('input', {'name': 'hsid'})['value'],
                'cid': bs.find('input', {'name': 'cid'})['value'],
                'rdsToken': bs.find('input', {'name': 'rdsToken'})['value'],
                'umidToken': bs.find('input', {'name': 'umidToken'})['value'],
                '_csrf_token': bs.find('input', {'name': '_csrf_token'})['value'],
                'checkCode': captcha}
            logger.debug('taobao post data' + str(data))

            ret = self._safe_post('https://passport.alipay.com/newlogin/login.do?fromSite=0',
                         headers={
                            'Referer':'https://passport.alipay.com/mini_login.htm',
                            'User-agent': 'Mozilla/5.0'},
                         data=data).content

            jdata = json.loads(ret)

            # 出错处理
            if jdata['content']['status'] == -1:
                logger.debug('error,' + str(jdata))
                if jdata['content'].get('data', {}).get('checkCodeLink'):
                    session_id = bs.find('input', {'name': 'cid'})['value']
                    captcha_url = 'http://pin.aliyun.com/get_img?identity=passport.alipay.com&sessionID=%s' % session_id
                    logger.debug('captcha url:' + captcha_url)
                    captcha = self.captcha_func(self._safe_get(captcha_url, headers={'User-agent': 'Mozilla/5.0'}).content)
                    continue  # 重新提交一次
                else:
                    if jdata['content']['data'].get('titleMsg', '') == u'\u9a8c\u8bc1\u7801\u9519\u8bef\uff0c\u8bf7\u91cd\u65b0\u8f93\u5165':
                        print 'Wrong captcha'
                        captcha = ''
                        continue
                    raise Xiamiexp('unknown')

            # 登录成功, 将 st 传递给虾米
            st = jdata['content']['data']['st']
            logger.debug('st=' + st)

            ret = self._safe_get('http://www.xiami.com/accounts/back?st=' + st,
                        headers={'Referer':'https://passport.alipay.com/mini_login.htm',
                                 'User-agent': 'Mozilla/5.0'})

            # 由此登录完成
            return

    def from_cookies(self, cookies):
        """通过cookies登录, 需要提交 dict 形式的cookies"""
        for k, v in cookies.items():
            self.session.cookies.set(k, v)

    @Utils.check_username
    def _get_uid(self):
        url = 'http://www.xiami.com/vip/myvip'
        header = {'user-agent': 'Mozilla/5.0',
                  'Referer': 'http://img.xiami.com/staticmethod/swf/seiya/player.swf?v=1394535902294'}
        ret = self._safe_get(url, headers=header).content
        user_id = re.findall('loginMemberUid = \'(\d+)\'', ret)[0]
        logger.debug('_get_uid, uid=' + user_id)
        self.account['uid'] = user_id

    @Utils.check_username
    def set_320k(self):
        header = {'user-agent': 'Mozilla/5.0',
                  'Referer': 'http://img.xiami.com/static/swf/seiya/player.swf?v=1394535902294'}
        user_id = self.account['uid']
        data = {'user_id': user_id,
                'tone_type': '1',
                '_xiamitoken': self.session.cookies.get('_xiamitoken')
                }
        ret = self._safe_post(
            'http://www.xiami.com/vip/update-tone', data=data, headers=header)
        ret = json.loads(ret.text)
        if ret['info'] == 'success':
            self.hq = True
            logger.debug('Quality of songs were set to 320Kbps')
        else:
            self.hq = False
            logger.error('Not vip')

    def get_stared_songs(self, uid=None, full=False):
        url = 'http://www.xiami.com/space/lib-song/u/{uid}/page/{page}'

        def _bs_func(bsobj):
            foo = bsobj.findAll(attrs={'class': 'song_name'})
            if not foo:
                return None
            lst = []
            for i in foo:
                lst.append(i.find('a')['href'].replace('http://www.xiami.com/song/', ''))
            return lst
        return self._lib_func(_bs_func, url, uid)

    def download_song(self, song_id):
        # 妈蛋,虾米把android的接口都弄跪了
        while True:
            
            song_info = self._safe_get(
                'http://www.xiami.com/song/playlist/id/%s' % (song_id),
                headers={'user-agent': 'Mozilla/5.0'}).content
            try:
                jdata = xmltodict.parse(song_info)
                break
            except:
                logger.debug('song_id:%s failed to parse xml, get new sec' % song_id)
                sec = re.findall('sec=(.*?);', song_info)[0]
                # update sec in cookies
                self.session.cookies['sec'] = sec
                continue

        info = jdata['playlist']['trackList']['track']
        if self.hq:
            info['location'] = Utils.url_decrypt(json.loads(self._safe_get(
                'http://www.xiami.com/song/gethqsong/sid/'
                + song_id, headers=Utils.header).content)['location'])
        return info

    def _download_multi(self, album_id, stype):
        info = {}
        album_info = self._safe_get('http://www.xiami.com/song/playlist/id/'
                                      '%s/type/%s' % (album_id, stype),
                                      headers={'User-Agent': 'Mozilla/5.0'}).content
        data = xmltodict.parse(album_info)['playlist']['trackList']['track']

        info['header'] = Utils.header
        info['cookies'] = self.session.cookies.get_dict()
        info['data'] = []

        for song in data:
            if self.hq:
                url = Utils.url_decrypt(json.loads(self._safe_get(
                    'http://www.xiami.com/song/gethqsong/sid/'
                    + song['song_id'], headers=Utils.header).content)['location'])
            else:
                url = Utils.url_decrypt(song['location'])

            info['data'].append({'id': song['song_id'],
                                 'title': song['title'],
                                 'album_id': song['album_id'],
                                 'album_name': song['album_name'],
                                 'lyric': song['lyric'],
                                 'artist': song['artist'],
                                 'album_pic': song['album_pic'],
                                 'length': song['length'],
                                 'url': url
                                 })

        return info

    def download_album(self, album_id):
        return self._download_multi(album_id, 1)

    def download_playlist(self, col_id):
        return self._download_multi(col_id, 3)

    def star_song(self, songid):
        # android 的 fav 接口已经不能用了
        header = {'user-agent': 'Mozilla/5.0',
                  'Referer': 'http://img.xiami.com/static/swf/'
                             'seiya/player.swf?v=1394535902294'}
        data = {'tags': '',
                'type': '3',
                'id': songid,
                'desc': '',
                'grade': 5,
                'share': 0,
                'shareTo': 'all',
                '_xiamitoken': self.session.cookies.get('_xiamitoken')
                }
        ret = self._safe_post(
            'http://www.xiami.com/ajax/addtag', headers=header, data=data)
        try:
            if json.loads(ret.content)['status'] == 'ok':
                logger.info('star song:' + str(songid))
            else:
                logger.error('User not logged in.')
        except:
            print ret.content



    def _lib_func(self, func, url, uid=None):
        """
        :param func: 调用的接口
        :param func: 对条目的处理函数
        """
        if not uid:
            if not 'uid' in self.account:
                return
            uid = self.account['uid']
        page = 1
        obj_list = []
        while True:
            logger.debug('get ' + url.format(uid=uid, page=page))
            content = self._safe_get(
                url.format(uid=uid, page=page), headers=Utils.header).content

            bs = BeautifulSoup(content)
            foo = func(bs)
            if not foo:
                break
            obj_list.extend(foo)

            page = page + 1
        return obj_list

    def get_stared_collections(self, uid=None):
        url = 'http://www.xiami.com/space/collect-fav/u/{uid}/page/{page}'

        def _bs_func(bsobj):
            foo = bsobj.findAll(attrs={'class': 'name'})
            if not foo:
                return None
            lst = []
            for i in foo:
                lst.append(i.find('a')['href'].replace('/collect/', ''))
            return lst
        return self._lib_func(_bs_func, url, uid)

    def get_stared_albums(self, uid=None):
        url = 'http://www.xiami.com/space/lib-album/u/{uid}/page/{page}'

        def _bs_func(bsobj):
            foo = bsobj.findAll(attrs={'class': 'name'})
            if not foo:
                return None
            lst = []
            for i in foo:
                lst.append(i.find('a')['href'].replace('/album/', ''))
            return lst

        return self._lib_func(_bs_func, url, uid)

    def get_session(self):
        """获得requests的session
        """
        return self.session
    """
    @Utils.check_username
    def get_graded_songs(self):
        url = 'http://www.xiami.com/playersong/getgradesong'
        content = self._safe_get(url, headers=Utils.header).content
        return [i['song_id'] for i in json.loads(content)['data']['songs']]
    """

    @Utils.check_username
    def add_new_playlog(self, song_id):
        url = 'http://www.xiami.com/app/android/playlog?id={0}&uid={1}' % (
            song_id)
        content = self._safe_get(url, headers=Utils.header).content
        return json.loads(content)['status']

    def get_random_songs(self, uid=None, full=False):
        if uid is None:
            if 'uid' in self.account:
                return
            uid = self.account['uid']

        url = 'http://www.xiami.com/app/android/rnd?uid=%s' % uid
        content = self._safe_get(url, headers=Utils.header).content
        if content == '':
            return
        jdata = json.loads(content)
        if full:
            return jdata['songs']
        else:
            return [song['song_id'] for song in jdata['songs']]

    def get_artist_topsongs(self, artist_id, full=False):
        url = 'http://www.xiami.com/app/android/artist-topsongs?id=%s' % artist_id
        content = self._safe_get(url, headers=Utils.header).content
        jdata = json.loads(content)
        if full:
            return jdata['songs']
        else:
            return [song['song_id'] for song in jdata['songs']]

    def get_artist_albums(self, artist_id, full=False):
        url = 'http://www.xiami.com/app/android/artist-albums?id={0}&page={1}'
        if full:
            return self._lib_func('albums', lambda x: x, uid=artist_id, url=url)
        else:
            return self._lib_func('albums', lambda x: x['album_id'],
                                  uid=artist_id, url=url)
 
