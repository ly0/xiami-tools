"""
  用途:转移 transferer 加星的歌曲到 transferee
  专业免费2个月vip 20年 =w=, 我一般用于新账户的推荐歌曲功能
"""
from xiami import *

xiami1 = Xiami(username='transferer', password='psasword1', taobao=True)
xiami2 = Xiami(username='transferee', password='password2', taobao=True)

stared = xiami1.get_graded_songs()
for item in stared:
    print 'staring song:', item
    xiami2.star_song(item)
