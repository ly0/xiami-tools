# coding=utf8
"""
    该脚本用于下载所有用户加星(收藏)的歌曲到 ./stared 目录下，并且内嵌专辑图片
"""

import os
import re
import time
import random
import urllib2
from xiami import *
import captcha
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC

# source: baidupcsapi repo Issue 3 on github
def upload_img42(img):
    url = 'http://img42.com'
    req = urllib2.Request(url, data=img)
    msg = urllib2.urlopen(req).read()
    return '%s/%s' % (url, json.loads(msg)['id'])

def captcha(jpeg):
    print '* captcha needed'
    print 'captcha url:', upload_img42(jpeg)
    foo = raw_input('captcha >')
    return foo

class Mutagentools:

    @staticmethod
    def add_tags(mp3, title=None, album=None, artist=None,
                 image_cover=None, image_artist=None, image_type=u'image/jpeg'):
        _id3 = {
            'mp3_title': TIT2(encoding=3, text=title),
            'mp3_artist': TPE1(encoding=3, text=artist),
            'mp3_album': TALB(encoding=3, text=album),
            'mp3_cover': APIC(3, image_type, 3, u'Front cover', image_cover),
            'mp3_artist_image': APIC(3, image_type, 8, u'Artist picture', image_artist),
        }
        # 尝试打开文件
        audio = MP3(mp3, ID3=ID3)
        try:
            audio.add_tags()
        except:
            pass

        for i in _id3.values():
            audio.tags.add(i)

        audio.save()


def safe_get(url):
    while True:
        try:
            foo = urllib2.urlopen(url).read()
            return foo
        except urllib2.HTTPError as e:
            if 'HTTP Error 503' in str(e):
                print '%s does not exist.' % url
                return None
            else:
                continue
        except:
            continue

xiami = Xiami(username='username', password='password', captcha_handler=captcha)
# xiami = Xiami(username='taobaousername', password='taobaopassword', taobao=True, captcha_handler=captcha)

xiami.set_320k()
cookies = ';'.join(['%s=%s' % (k, v)
                    for k, v in xiami.session.cookies.items()])

stared_list = xiami.get_stared_songs()

for entry in stared_list:
    song = xiami.download_song(entry)
    filepath = './stared/{0}-{1}.mp3'.format(
        Utils.text_validate(song['album_name']),
        Utils.text_validate(song['title']))
    cmd = 'axel --alternate -n5 -H "Cookies:{2}" "{0}" -o "{1}"'.format(
        song['location'], filepath, cookies)

    song_logo = re.sub('_\d+', '', song['album_pic'])
    os.system(cmd)

    logo_song = safe_get(song_logo)

    # mutagen area
    Mutagentools.add_tags(filepath, song['title'], song['album_name'], song[
                          'artist'], logo_song)

