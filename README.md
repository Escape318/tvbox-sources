# tvbox-sources

盒子正式影视源的 GitHub 副本（13 站），**所有中转站已改为直连**。

## 导入地址

```
https://raw.githubusercontent.com/Escape318/tvbox-sources/main/tvbox.json
```

## 站点

| 站名 | 采集接口 |
|---|---|
| 荐片 | 自建爬虫 |
| 百度云影视 | api.apibdzy.com |
| 追剧影视 | api.zuidapi.com |
| 非凡影视 | api.ffzyapi.com |
| 红牛影视 | www.hongniuzy2.com |
| 360影视 | 360zy.com |
| 暴风影视 | bfzyapi.com |
| 豪华影视 | hhzyapi.com |
| 极速影视 | jszyapi.com |
| 量子影视 | cj.lziapi.com |
| 无尽资源 | api.wujinapi.com |
| 光速资源 | api.guangsuapi.com |
| 金鹰资源 | jyzyapi.com |

## 说明

- 原盒子配置里的 4 个中转站（追剧·中转、百度云·中转、暴风·中转、豪华·中转、极速·中转、量子·中转）全部拆掉 `relay:` 前缀改成直连；其中追剧、百度云两者与已有直连站完全重复，已合并去重，所以总数 15 → 13。
- 爬虫脚本仍指向盒子的 `/cms.py`、`/jianpian.py`，所以这份配置依赖盒子在线；盒子上原有的配置（含中转站）没有改动。
- 这份配置不含中转，任何请求都不经过盒子 `/proxy`，但盒子本身要活着才能拉到爬虫脚本。
