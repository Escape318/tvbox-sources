# tvbox-sources

盒子上的正式影视源 + 爬虫，GitHub 备份。**这份配置不依赖盒子**：爬虫和采集接口都走直连。

## 目录

| 路径 | 内容 |
|---|---|
| `tvbox.json` | 站配置，13 站，`api` 指向本仓库爬虫，无 `relay:` |
| `spider/cms.py` | 通用 maccms 爬虫，与盒子 `/opt/tvbox/cms.py` 逐字节一致 |
| `spider/jianpian.py` | 荐片爬虫，与盒子 `/opt/tvbox/public/jianpian.py` 逐字节一致 |
| `config/sources-pool.json` | 源池登记表（15 条，含中转站，是盒子的运行态） |

## 导入地址

```
https://raw.githubusercontent.com/Escape318/tvbox-sources/main/tvbox.json
```

## 站点（13 站）

荐片、百度云影视、追剧影视、非凡影视、红牛影视、360影视、暴风影视、豪华影视、极速影视、量子影视、无尽资源、光速资源、金鹰资源。

## 说明

- 爬虫不动，`api` 指向 `spider/cms.py` / `spider/jianpian.py` 的 raw 地址，盒子宕机不影响拉脚本。
- 中转站（追剧、百度云、暴风、豪华、极速、量子）已拆 `relay:` 前缀改直连；追剧、百度云拆完后与已有直连站完全重复，已去重，所以 15 → 13。
- 直播 `lives` 指向公共上游 `live.fanmingming.com/tv/m3u/itv.m3u`，不再走盒子的 `live.json`（盒子那份是三源合并的 104KB 产物，仅盒子自用）。
- 爬虫里的 `RELAY` 常量写死了盒子中转地址，直连模式用不到；若以后又用 `relay:` 前缀，换服务器必须同步改它。
- 国内直连 GitHub raw 可能慢或被拦，脚本地址可换成 jsdelivr 镜像：`https://cdn.jsdelivr.net/gh/Escape318/tvbox-sources@main/spider/cms.py`（实测同字节，但分支缓存有延迟）。
- 盒子上的 `/opt/tvbox/public/vod.json` 未被改动，仍是 15 站含 6 个中转。
