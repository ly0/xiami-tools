"""
  用途:转移 transferer 加星的歌曲到 transferee
  专业免费2个月vip 20年 =w=, 我一般用于新账户的推荐歌曲功能
"""
from xiami import *

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

xiami1 = Xiami(username='transferer', password='psasword1', taobao=True, captcha_handler=captcha)
xiami2 = Xiami(username='transferee', password='password2', taobao=True, captcha_handler=captcha)

stared = xiami1.get_stared_songs()
for item in stared:
    print 'staring song:', item
    xiami2.star_song(item)
