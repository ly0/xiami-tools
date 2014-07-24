虾米工具包
============

* `Xiami.get_stared_song(self, uid=None)` 返回某用户所有收藏曲目列表, uid不写默认为登录用户. (测试速度过快会被ban, 一页等待1s)
* `Xiami.get_stared_collection(self, uid=None)` 返回某用户所有收藏精选集列表, uid不写默认为登录用户.
* `Xiami.get_stared_collection(self, uid=None)` 返回某用户所有收藏专集列表, uid不写默认为登录用户.
* `Xiami.set_320k()` 设置当前用户默认下载曲目为高音质
* `Xiami.download_song(self, song_id)` 返回编号为 *song_id* 的曲目的相关信息和下载地址, 详细返回请看范例
* `Xiami.download_album(self, album_id)` 返回编号为 *album_id* 的专辑的相关信息和专辑内曲目下载地址, 详细返回请看范例
* `Xiami.download_playlist(self, col_id)` 同上
* `Xiami.star_song(self, songid)` 收藏曲目编号为 *songid* 的歌曲

#### 范例


#### 转移用户收藏数据
2 + 3
