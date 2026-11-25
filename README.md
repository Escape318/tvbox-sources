# tvbox-sources

自建 FongMi / TVBox 源池配置，每日自动体检后发布，只保留验证通过的站点。

## 导入地址

```
https://raw.githubusercontent.com/Escape318/tvbox-sources/main/tvbox.json
```

在 FongMi「设置 → 配置地址」里粘贴该地址即可；站点列表为空时先刷新订阅。

## 站点（15）

| 站名 | 类型 |
|---|---|
| 荐片 | 自建爬虫 |
| 百度云影视 / 百度云·中转 | maccms |
| 追剧影视 / 追剧·中转 | maccms |
| 非凡影视 | maccms |
| 红牛影视 | maccms |
| 360影视 | maccms |
| 暴风影视·中转 | maccms |
| 豪华影视·中转 | maccms |
| 极速影视·中转 | maccms |
| 量子影视·中转 | maccms |
| 光速资源 | maccms |
| 金鹰资源 | maccms |
| 自动·api.wujinapi.com | maccms（自动发现，观察中） |

## 关于线路

很多站点的播放线路有两条，其中名字像 `feifan`、`liangzi`、`hhyun`、`jsyun` 的那条是**分享页/播放页**，不是 m3u8 直链。配套爬虫会自动把它换成真实地址：`/play/<hash>` 补 `/index.m3u8`、抓页面时补请求头、从页面里抠带 `sign` 的相对直链。所以两条线路正常情况下都能播。

## 说明

- 本仓库只有配置文件，爬虫脚本托管在配置里指向的自建服务器上。
- 德国机房出口被部分站方限制 IP 时，对应站点会在体检里标为「取流未验证，保留观察」，这不影响国内网络下的使用。
- 配置每日 06:00 全量体检后更新；00/12/18:20 另有轻检。
